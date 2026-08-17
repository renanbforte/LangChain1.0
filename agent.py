# =============================================================================
# agent.py  —  Agente de IA didático com LangChain + LangGraph + PostgreSQL
# -----------------------------------------------------------------------------
# Este arquivo junta TUDO o que foi explicado no README:
#   - Lê segredos do .env (chaves de API e URL do banco).
#   - Cria o modelo de linguagem (gpt-3.5-turbo, trocável por Gemini).
#   - Dá ao agente uma personalidade (system_prompt).
#   - Dá ao agente VÁRIAS tools (busca web + pacote tools/: CEP e temperatura).
#   - Trata erros de qualquer tool num ponto central (middleware).
#   - Resume conversas longas para não estourar a janela de contexto (middleware).
#   - Guarda a memória do agente no PostgreSQL (checkpointer).
#   - Salva o histórico em TEXTO LIMPO nas suas próprias tabelas.
#   - Roda um loop de conversa pelo terminal.
#
# Cada linha está comentada. Leia de cima para baixo como se fosse um livro.
# =============================================================================


# -----------------------------------------------------------------------------
# BLOCO 1 — IMPORTS (trazer as ferramentas que vamos usar)
# -----------------------------------------------------------------------------
# `import X` = "traga a biblioteca X para eu poder usar aqui".

import os                              # Biblioteca padrão do Python para ler variáveis de ambiente.
from dotenv import load_dotenv         # Função que lê o arquivo .env e joga os valores no ambiente.

# create_agent: a função do LangChain 1.0 que monta um agente pronto para uso.
from langchain.agents import create_agent

# SummarizationMiddleware: um "meio de campo" que RESUME conversas longas
# automaticamente, para não estourar a janela de contexto do modelo (ver README).
from langchain.agents.middleware import SummarizationMiddleware

# TavilySearch: a ferramenta (tool) que faz busca na web.
from langchain_tavily import TavilySearch

# PostgresSaver: o "checkpointer" do LangGraph que salva a memória no PostgreSQL.
from langgraph.checkpoint.postgres import PostgresSaver

# psycopg: o driver que permite ao Python conversar diretamente com o PostgreSQL
#          (usado para salvar o histórico nas NOSSAS tabelas de texto limpo).
import psycopg

# O NOSSO pacote de tools (a pasta tools/). Importamos só a "vitrine":
#   TOOLS                -> a lista com todas as tools do projeto (CEP, temperatura...).
#   tratar_erros_de_tool -> o middleware que trata erros de QUALQUER tool num lugar só.
# Repare como o agente não sabe em quais arquivos as tools moram — só usa a vitrine.
from tools import TOOLS, tratar_erros_de_tool


# -----------------------------------------------------------------------------
# BLOCO 2 — CARREGAR OS SEGREDOS DO .env
# -----------------------------------------------------------------------------
# load_dotenv() lê o arquivo .env e coloca cada variável dentro de os.environ.
# A partir daqui, bibliotecas como langchain-openai encontram OPENAI_API_KEY
# sozinhas, sem precisarmos passar a chave na mão. NUNCA escrevemos a chave
# no código — ela mora só no .env, que é ignorado pelo Git.
load_dotenv()

# Lemos a URL do banco do ambiente. os.environ["X"] busca a variável X.
# Se ela não existir, o programa para com erro claro (bom para não rodar sem banco).
DATABASE_URL = os.environ["DATABASE_URL"]

# --- Configuração do controle de memória (sumarização de conversas longas) ---
# Diferença importante entre os.environ[...] e os.getenv(...):
#   os.environ["X"]      -> se X NÃO existir, o programa PARA com erro (obrigatória).
#   os.getenv("X", pad)  -> se X não existir, usa o valor padrão "pad" (opcional).
# Como estas três são OPCIONAIS (têm padrão), usamos os.getenv.

# ESTRATEGIA_MEMORIA: como decidir a hora de resumir. Valores: "tokens" ou
# "mensagens". Se não estiver no .env, o padrão é "tokens".
ESTRATEGIA_MEMORIA = os.getenv("ESTRATEGIA_MEMORIA", "tokens")

# Os valores do .env chegam SEMPRE como TEXTO (string). Como estes são números,
# convertemos com int(...). Ex.: o texto "3000" vira o número 3000.
# O 2º argumento do getenv é o padrão (também em texto) caso não esteja no .env.

# MAX_TOKENS_RESUMO: usado na estratégia "tokens". Quando o histórico passar
# desse tanto de tokens, o middleware resume. Padrão: 3000.
MAX_TOKENS_RESUMO = int(os.getenv("MAX_TOKENS_RESUMO", "3000"))

# MAX_MENSAGENS_RESUMO: usado na estratégia "mensagens". Quando o histórico
# passar desse número de mensagens, o middleware resume. Padrão: 40.
MAX_MENSAGENS_RESUMO = int(os.getenv("MAX_MENSAGENS_RESUMO", "40"))


# -----------------------------------------------------------------------------
# BLOCO 3 — AS FERRAMENTAS (TOOLS) DO AGENTE
# -----------------------------------------------------------------------------
# Uma "tool" é uma função que o agente PODE decidir chamar sozinho quando
# achar que precisa. Ele não é obrigado — ele lê a sua pergunta e decide qual
# (ou nenhuma) usar. Aqui o agente terá VÁRIAS tools convivendo:
#   - busca_web       -> busca na web (Tavily), definida aqui mesmo.
#   - TOOLS           -> as tools do pacote tools/ (CEP e temperatura).
#
# TavilySearch faz uma busca na web e devolve os resultados.
#   max_results=3  -> traz no máximo 3 resultados por busca (suficiente e barato).
busca_web = TavilySearch(max_results=3)

# Montamos a lista FINAL de tools do agente.
# O `*TOOLS` "desempacota" a lista do pacote: [busca_web, conversor..., buscar_cep].
# Assim juntamos a tool local (busca_web) com todas as tools do pacote de uma vez.
#
# >>> PARA ADICIONAR UMA NOVA TOOL NO FUTURO:
# >>>   - Se for uma tool "de verdade" (CEP, clima, cotação...), crie no pacote
# >>>     tools/ e registre em tools/__init__.py -> ela entra sozinha pelo *TOOLS.
# >>>   - Se for uma tool "de biblioteca" (como a Tavily), some ela aqui na lista.
todas_as_tools = [busca_web, *TOOLS]


# -----------------------------------------------------------------------------
# BLOCO 4 — A PERSONALIDADE DO AGENTE (system_prompt)
# -----------------------------------------------------------------------------
# O system_prompt são as "instruções permanentes" do agente: quem ele é e
# como deve se comportar. Ele vale para a conversa inteira.
SYSTEM_PROMPT = (
    "Você é um assistente prestativo e direto, que responde em português do Brasil. "
    "Você tem ferramentas para: buscar na web, converter temperaturas e consultar "
    "endereços por CEP. Escolha a ferramenta certa para cada pedido; se nenhuma se "
    "aplicar, responda com seu próprio conhecimento. Quando a pergunta envolver fatos "
    "atuais ou algo de que você não tem certeza, use a busca na web antes de responder."
)


# -----------------------------------------------------------------------------
# BLOCO 4b — A FÁBRICA DO AGENTE (monta o "grafo"; reusada pelo terminal e Studio)
# -----------------------------------------------------------------------------
# Por que uma função separada? Porque duas coisas diferentes precisam montar o
# MESMO agente, e não queremos copiar o código em dois lugares:
#   1) o loop de terminal (main), que passa o PostgresSaver como checkpointer;
#   2) o LangGraph Studio (via langgraph.json), que precisa de um grafo montável
#      "de fora". O Studio gerencia a persistência dele, então chamamos sem
#      checkpointer nesse caso.
# Extrair para uma fábrica é a mesma ideia de separação de responsabilidades das
# tools: montar o agente vira uma peça reutilizável e testável.
def construir_agente(checkpointer=None):
    """Monta e devolve o agente (o 'grafo' do LangGraph) com tools + middlewares.

    checkpointer: onde salvar a memória. No terminal passamos o PostgresSaver;
                  no Studio deixamos None (a plataforma cuida da persistência).
    """
    # Modelo de linguagem (string "provedor:modelo"). Trocar aqui troca em tudo.
    modelo = "openai:gpt-3.5-turbo"
    # Para o Gemini no futuro:  modelo = "google_genai:gemini-1.5-flash"

    # Monta a regra de sumarização a partir da estratégia lida do .env (BLOCO 2).
    #   ("tokens", N)   -> resume quando o histórico passa de N tokens.
    #   ("messages", N) -> resume quando o histórico passa de N mensagens.
    if ESTRATEGIA_MEMORIA == "tokens":
        gatilho = ("tokens", MAX_TOKENS_RESUMO)
    elif ESTRATEGIA_MEMORIA == "mensagens":
        gatilho = ("messages", MAX_MENSAGENS_RESUMO)
    else:
        # Valor inesperado no .env -> avisa e cai no padrão seguro (tokens).
        print(f"[aviso] ESTRATEGIA_MEMORIA='{ESTRATEGIA_MEMORIA}' invalida; usando 'tokens'.")
        gatilho = ("tokens", MAX_TOKENS_RESUMO)

    # O middleware de sumarização usa o MESMO modelo do agente para os resumos.
    memoria_middleware = SummarizationMiddleware(model=modelo, trigger=gatilho)

    # Junta tudo e devolve o grafo pronto.
    #   middleware: a ORDEM importa; erro de tool primeiro, sumarização depois.
    return create_agent(
        model=modelo,
        tools=todas_as_tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
        middleware=[tratar_erros_de_tool, memoria_middleware],
    )


# -----------------------------------------------------------------------------
# BLOCO 4c — GRAFO PARA O LANGGRAPH STUDIO (o alvo do langgraph.json)
# -----------------------------------------------------------------------------
# O arquivo langgraph.json aponta para esta função (agent.py:criar_grafo).
# Quando você roda `langgraph dev`, o Studio IMPORTA e CHAMA criar_grafo() para
# desenhar e executar o agente no painel visual. Passamos checkpointer=None
# porque, no Studio, a própria plataforma cuida de guardar o estado.
def criar_grafo():
    """Fábrica de grafo para o LangGraph Studio (usada pelo langgraph.json)."""
    return construir_agente(checkpointer=None)


# -----------------------------------------------------------------------------
# BLOCO 5 — FUNÇÕES QUE SALVAM O HISTÓRICO EM TEXTO LIMPO (NAS NOSSAS TABELAS)
# -----------------------------------------------------------------------------
# O LangGraph guarda a memória dele nas tabelas "checkpoints" em formato jsonb
# (ótimo para a máquina, ilegível para humanos). Por isso mantemos as NOSSAS
# tabelas "conversas" e "mensagens" em paralelo, só para LEITURA humana.

def garantir_conversa(conn, thread_id):
    """Garante que exista UMA linha na tabela 'conversas' para este thread_id
    e devolve o 'id' (número) dessa conversa."""
    # `conn.cursor()` abre um "cursor": o canal por onde enviamos comandos SQL.
    # O `with` fecha o cursor sozinho no fim, mesmo que dê erro no meio.
    with conn.cursor() as cur:
        # Tentamos INSERIR uma nova conversa com este thread_id.
        #   ON CONFLICT (thread_id) DO NOTHING -> se JÁ existir uma conversa com
        #       esse thread_id (lembra do UNIQUE na tabela?), não faça nada,
        #       em vez de dar erro de duplicidade.
        #   RETURNING id -> peça ao banco para DEVOLVER o id da linha inserida.
        # Passamos o valor via %s (query parametrizada) e a tupla (thread_id,).
        cur.execute(
            """
            INSERT INTO conversas (thread_id)
            VALUES (%s)
            ON CONFLICT (thread_id) DO NOTHING
            RETURNING id
            """,
            (thread_id,),
        )
        # fetchone() pega a primeira linha do resultado.
        # Se a inserção ACONTECEU, o RETURNING devolve o id -> linha != None.
        linha = cur.fetchone()
        if linha is not None:
            # Havia RETURNING: pegamos o id recém-criado (posição 0 da linha).
            conversa_id = linha[0]
        else:
            # ON CONFLICT pulou a inserção (conversa já existia), então o
            # RETURNING não devolveu nada. Buscamos o id que já está no banco.
            cur.execute(
                "SELECT id FROM conversas WHERE thread_id = %s",
                (thread_id,),
            )
            conversa_id = cur.fetchone()[0]
    # commit() confirma (grava de verdade) as mudanças no banco.
    conn.commit()
    # Devolvemos o id para quem chamou a função poder usar ao salvar mensagens.
    return conversa_id


def salvar_mensagem(conn, conversa_id, papel, conteudo):
    """Insere UMA mensagem na tabela 'mensagens', ligada à conversa dona dela."""
    with conn.cursor() as cur:
        # Inserimos papel ('user' ou 'assistant') e o texto da mensagem.
        #
        # POR QUE %s E NÃO f-string?  -> SEGURANÇA (proteção contra SQL injection).
        # Se montássemos a query com f-string, tipo:
        #     f"INSERT ... VALUES ('{conteudo}')"
        # e o texto contivesse aspas ou comandos SQL, um usuário mal-intencionado
        # poderia INJETAR comandos e destruir/roubar dados. Com %s, o driver
        # psycopg trata o valor como DADO puro (nunca como comando). Sempre %s.
        cur.execute(
            "INSERT INTO mensagens (conversa_id, papel, conteudo) VALUES (%s, %s, %s)",
            (conversa_id, papel, conteudo),
        )
    conn.commit()  # Confirma a gravação da mensagem.


# -----------------------------------------------------------------------------
# BLOCO 6 — O PROGRAMA PRINCIPAL (monta o agente e roda o loop de conversa)
# -----------------------------------------------------------------------------
def main():
    # -- 6.1  Conexão "crua" com o banco, para NOSSAS tabelas de texto limpo ---
    # psycopg.connect abre uma conexão direta com o PostgreSQL usando a URL do .env.
    # Guardamos em `conn` e vamos usar nas funções garantir_conversa/salvar_mensagem.
    conn = psycopg.connect(DATABASE_URL)

    # -- 6.2  O checkpointer (memória do agente no PostgreSQL) ------------------
    # PostgresSaver.from_conn_string(...) devolve um "context manager": por isso
    # usamos `with`. O `with` garante que a conexão do checkpointer seja ABERTA
    # no começo do bloco e FECHADA corretamente no fim (mesmo se ocorrer erro).
    with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        # setup() cria as tabelas internas do LangGraph (checkpoints etc.) SE
        # elas ainda não existirem. É seguro chamar toda vez: na primeira, cria;
        # nas próximas, apenas confere que já está tudo lá.
        checkpointer.setup()

        # -- 6.3  Monta o agente usando a fábrica construir_agente (BLOCO 4b) ---
        # Passamos o checkpointer do Postgres para o agente ter MEMÓRIA persistente.
        # O mesmo builder é reusado pelo LangGraph Studio (lá sem checkpointer).
        agente = construir_agente(checkpointer)

        # -- 6.5  Identificador da conversa (thread_id) ------------------------
        # O thread_id separa conversas diferentes na memória. Mesmo thread_id =
        # o agente LEMBRA do que já foi dito. Trocar o thread_id = começar do zero.
        #
        # Aqui PERGUNTAMOS qual conversa abrir, para você ter conversas DISTINTAS:
        #   - input(...) mostra o texto e espera você digitar + Enter.
        #   - .strip() remove espaços sobrando nas pontas.
        #   - `or "conversa-1"` é um atalho: se você apertar Enter sem digitar
        #     nada, o texto vira vazio ("") e o Python usa o valor da direita
        #     ("conversa-1") como padrão. Se você digitou algo, ele usa o que
        #     você digitou.
        # Exemplos: digite "trabalho" hoje e amanhã -> ele CONTINUA essa conversa.
        #           digite "pessoal" -> conversa SEPARADA, do zero, isolada.
        thread_id = input("Nome da conversa (Enter para 'conversa-1'): ").strip() or "conversa-1"

        # config é um dicionário que passamos ao agente em toda chamada.
        # "configurable" -> "thread_id" diz ao checkpointer QUAL conversa é esta.
        config = {"configurable": {"thread_id": thread_id}}

        # Garante que a NOSSA tabela 'conversas' tenha a linha desta sessão e
        # guarda o id numérico para usar ao salvar cada mensagem.
        conversa_id = garantir_conversa(conn, thread_id)

        # -- 6.6  Mensagens de boas-vindas no terminal -------------------------
        # f"..." é uma f-string: o que está dentro de {} é substituído pelo valor
        # da variável. Aqui mostramos qual conversa (thread_id) foi aberta.
        # (Repare: usamos f-string SÓ para exibir texto na tela. Para SQL, nunca.)
        print(f"Agente pronto! Conversa aberta: '{thread_id}'.")
        print("Digite sua mensagem. Para sair, digite: sair\n")

        # -- 6.7  O LOOP DE CONVERSA -------------------------------------------
        # `while True` repete para sempre, até darmos um `break` para parar.
        while True:
            # input(...) mostra o texto e ESPERA você digitar e apertar Enter.
            # O que você digitar fica guardado na variável `pergunta`.
            pergunta = input("Você: ")

            # Se você digitar "sair" (em qualquer caixa), encerramos o loop.
            #   .strip() remove espaços sobrando; .lower() ignora maiúsculas.
            if pergunta.strip().lower() == "sair":
                print("Até logo!")
                break  # `break` sai do `while` e o programa termina.

            # Salvamos a SUA pergunta na tabela 'mensagens' com papel 'user'.
            salvar_mensagem(conn, conversa_id, "user", pergunta)

            # Chamamos o agente. Entregamos a pergunta no formato que ele espera:
            #   um dicionário com a chave "messages", contendo uma lista de
            #   mensagens; cada mensagem tem "role" (papel) e "content" (texto).
            # Passamos também o `config` para ele saber de qual conversa lembrar.
            resultado = agente.invoke(
                {"messages": [{"role": "user", "content": pergunta}]},
                config,
            )

            # O agente devolve o histórico atualizado em resultado["messages"].
            # A ÚLTIMA mensagem da lista ([-1]) é a resposta dele; .content é o texto.
            resposta = resultado["messages"][-1].content

            # Salvamos a RESPOSTA do agente na tabela 'mensagens' com papel 'assistant'.
            salvar_mensagem(conn, conversa_id, "assistant", resposta)

            # Mostramos a resposta no terminal. \n pula uma linha para dar respiro.
            print(f"Agente: {resposta}\n")

    # -- 6.8  Fechamento -------------------------------------------------------
    # Ao sair do `with`, o checkpointer já foi fechado. Aqui fechamos também a
    # nossa conexão "crua" com o banco, liberando o recurso.
    conn.close()


# -----------------------------------------------------------------------------
# BLOCO 7 — PONTO DE ENTRADA + ESPAÇO RESERVADO PARA O WEBHOOK (FUTURO)
# -----------------------------------------------------------------------------
# Esta linha significa: "se este arquivo foi executado diretamente (e não
# importado por outro), então rode a função main()". É o padrão em Python
# para ter um ponto de partida claro.
if __name__ == "__main__":
    main()


# =============================================================================
# FUTURO — RECEBER MENSAGENS VIA WEBHOOK (NÃO IMPLEMENTADO AINDA)
# -----------------------------------------------------------------------------
# Hoje o agente conversa pelo terminal (input/print). No futuro, você pode
# querer que um sistema EXTERNO (um site, o WhatsApp, outro programa) mande
# uma mensagem e receba a resposta do agente por HTTP. Isso se chama "webhook":
# um endereço (endpoint) que fica esperando requisições.
#
# IDEIA-CHAVE: o thread_id, que hoje vem do input(), no webhook viria DE FORA,
# dentro da requisição. Cada sistema/cliente manda o SEU thread_id (ex.: o
# número de telefone), e você ganha memória isolada por conversa de graça.
#
# ATENÇÃO À PERFORMANCE: monte o agente UMA VEZ só, quando o servidor inicia
# (fora do endpoint). Se montar dentro do @app.post, ele reconstruiria tudo a
# cada requisição — lento e desnecessário. Por isso, no esboço abaixo, o
# checkpointer e o create_agent ficam LÁ EM CIMA, e o endpoint só faz o invoke.
#
# Esboço (comentado — precisaria instalar fastapi e uvicorn para rodar):
#
#   from fastapi import FastAPI               # framework web leve para criar a API
#   from pydantic import BaseModel            # ajuda a descrever o formato da requisição
#
#   # --- MONTAGEM ÚNICA (roda 1x quando o servidor sobe) ---------------------
#   load_dotenv()                             # carrega os segredos do .env
#   _conn = psycopg.connect(DATABASE_URL)     # conexão para as tabelas de texto limpo
#   _cm = PostgresSaver.from_conn_string(DATABASE_URL)  # abre o checkpointer...
#   _checkpointer = _cm.__enter__()           # ...e o mantém aberto durante a vida do servidor
#   _checkpointer.setup()                     # garante as tabelas internas do LangGraph
#   _agente = create_agent(                   # monta o agente UMA vez
#       model="openai:gpt-3.5-turbo",
#       tools=tools,
#       system_prompt=SYSTEM_PROMPT,
#       checkpointer=_checkpointer,
#   )
#
#   app = FastAPI()                           # cria a aplicação web
#
#   class Entrada(BaseModel):                 # descreve o corpo esperado da requisição:
#       thread_id: str                        #   qual conversa (vem de fora!)
#       mensagem: str                         #   o texto que o usuário mandou
#
#   @app.post("/webhook")                     # endpoint que recebe POST em /webhook
#   def receber(dados: Entrada):              # 'dados' já vem validado (thread_id + mensagem)
#       # CUIDADO: valide o thread_id, pois veio de fora (não confie cegamente).
#       thread_id = dados.thread_id.strip()   # tira espaços das pontas
#       if not thread_id:                     # se veio vazio, recuse a requisição
#           return {"erro": "thread_id vazio"}
#
#       config = {"configurable": {"thread_id": thread_id}}  # <- o thread_id de fora entra aqui
#       conversa_id = garantir_conversa(_conn, thread_id)    # garante a linha em 'conversas'
#       salvar_mensagem(_conn, conversa_id, "user", dados.mensagem)  # salva a pergunta
#
#       resultado = _agente.invoke(           # chama o agente já montado
#           {"messages": [{"role": "user", "content": dados.mensagem}]},
#           config,
#       )
#       resposta = resultado["messages"][-1].content         # extrai o texto
#       salvar_mensagem(_conn, conversa_id, "assistant", resposta)  # salva a resposta
#       return {"resposta": resposta}         # o FastAPI transforma isso em JSON
#
# Para rodar (no futuro):  uv run uvicorn agent:app --reload
# Deixamos apenas o PLANO comentado; nada disso executa agora.
# =============================================================================
