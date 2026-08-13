# =============================================================================
# agent.py  —  Agente de IA didático com LangChain + LangGraph + PostgreSQL
# -----------------------------------------------------------------------------
# Este arquivo junta TUDO o que foi explicado no README:
#   - Lê segredos do .env (chaves de API e URL do banco).
#   - Cria o modelo de linguagem (gpt-3.5-turbo, trocável por Gemini).
#   - Dá ao agente uma personalidade (system_prompt).
#   - Dá ao agente uma ferramenta de busca na web (Tavily).
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

# TavilySearch: a ferramenta (tool) que faz busca na web.
from langchain_tavily import TavilySearch

# PostgresSaver: o "checkpointer" do LangGraph que salva a memória no PostgreSQL.
from langgraph.checkpoint.postgres import PostgresSaver

# psycopg: o driver que permite ao Python conversar diretamente com o PostgreSQL
#          (usado para salvar o histórico nas NOSSAS tabelas de texto limpo).
import psycopg


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


# -----------------------------------------------------------------------------
# BLOCO 3 — AS FERRAMENTAS (TOOLS) DO AGENTE
# -----------------------------------------------------------------------------
# Uma "tool" é uma função que o agente PODE decidir chamar sozinho quando
# achar que precisa. Ele não é obrigado — ele lê a sua pergunta e decide.
#
# TavilySearch faz uma busca na web e devolve os resultados.
#   max_results=3  -> traz no máximo 3 resultados por busca (suficiente e barato).
busca_web = TavilySearch(max_results=3)

# A lista de tools que o agente terá disponível.
# >>> PARA ADICIONAR UMA NOVA TOOL NO FUTURO: crie/importe a tool acima e
# >>> simplesmente inclua ela nesta lista. Exemplo:
# >>>     tools = [busca_web, minha_nova_tool, outra_tool]
# O agente passa a considerar automaticamente todas as tools da lista.
tools = [busca_web]


# -----------------------------------------------------------------------------
# BLOCO 4 — A PERSONALIDADE DO AGENTE (system_prompt)
# -----------------------------------------------------------------------------
# O system_prompt são as "instruções permanentes" do agente: quem ele é e
# como deve se comportar. Ele vale para a conversa inteira.
SYSTEM_PROMPT = (
    "Você é um assistente prestativo e direto, que responde em português do Brasil. "
    "Quando a pergunta envolver fatos atuais ou algo que você não tem certeza, "
    "use a ferramenta de busca na web antes de responder."
)


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
    # -- 6.1  Escolha do modelo de linguagem -----------------------------------
    # No LangChain 1.0 podemos indicar o modelo por uma STRING no formato
    # "provedor:modelo". O create_agent cria o objeto do modelo por baixo.
    #   OpenAI (atual):
    modelo = "openai:gpt-3.5-turbo"
    #   PARA TROCAR PARA O GEMINI DEPOIS: comente a linha acima e descomente
    #   a de baixo (a chave GOOGLE_API_KEY precisa estar no .env).
    # modelo = "google_genai:gemini-1.5-flash"

    # -- 6.2  Conexão "crua" com o banco, para NOSSAS tabelas de texto limpo ---
    # psycopg.connect abre uma conexão direta com o PostgreSQL usando a URL do .env.
    # Guardamos em `conn` e vamos usar nas funções garantir_conversa/salvar_mensagem.
    conn = psycopg.connect(DATABASE_URL)

    # -- 6.3  O checkpointer (memória do agente no PostgreSQL) ------------------
    # PostgresSaver.from_conn_string(...) devolve um "context manager": por isso
    # usamos `with`. O `with` garante que a conexão do checkpointer seja ABERTA
    # no começo do bloco e FECHADA corretamente no fim (mesmo se ocorrer erro).
    with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        # setup() cria as tabelas internas do LangGraph (checkpoints etc.) SE
        # elas ainda não existirem. É seguro chamar toda vez: na primeira, cria;
        # nas próximas, apenas confere que já está tudo lá.
        checkpointer.setup()

        # -- 6.4  Montagem do agente -------------------------------------------
        # create_agent junta as 4 peças que preparamos:
        #   model         -> o cérebro (o LLM que raciocina e escreve).
        #   tools         -> as ferramentas que ele PODE usar (busca na web).
        #   system_prompt -> a personalidade/instruções permanentes.
        #   checkpointer  -> onde a memória de cada conversa é salva.
        agente = create_agent(
            model=modelo,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            checkpointer=checkpointer,
        )

        # -- 6.5  Identificador da conversa (thread_id) ------------------------
        # O thread_id separa conversas diferentes na memória. Mesmo thread_id =
        # o agente LEMBRA do que já foi dito. Trocar o thread_id = começar do zero.
        thread_id = "conversa-1"

        # config é um dicionário que passamos ao agente em toda chamada.
        # "configurable" -> "thread_id" diz ao checkpointer QUAL conversa é esta.
        config = {"configurable": {"thread_id": thread_id}}

        # Garante que a NOSSA tabela 'conversas' tenha a linha desta sessão e
        # guarda o id numérico para usar ao salvar cada mensagem.
        conversa_id = garantir_conversa(conn, thread_id)

        # -- 6.6  Mensagens de boas-vindas no terminal -------------------------
        print("Agente pronto! Digite sua mensagem.")
        print("Para sair, digite: sair\n")

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
# A ideia (esqueleto, para você preencher depois — precisaria instalar FastAPI):
#
#   from fastapi import FastAPI          # framework web leve para criar a API
#   app = FastAPI()                      # cria a aplicação web
#
#   @app.post("/webhook")                # cria o endpoint que recebe POST em /webhook
#   def receber(mensagem: str):          # 'mensagem' viria no corpo da requisição
#       # Aqui dentro você montaria o agente (igual ao main() acima),
#       # chamaria agente.invoke({"messages": [{"role": "user", "content": mensagem}]}, config)
#       # e devolveria a resposta:
#       resposta = "..."                 # resultado["messages"][-1].content
#       return {"resposta": resposta}    # o FastAPI transforma isso em JSON de resposta
#
# Para rodar (no futuro):  uv run uvicorn agent:app --reload
# Deixamos apenas o PLANO comentado; nada disso executa agora.
# =============================================================================
