# LangChain1.0 — Meu primeiro agente de IA (guia do zero)

Este é um guia **didático e completo** para construir um agente de IA em Python
usando **LangChain 1.0 + LangGraph**, com **memória salva no PostgreSQL** e um
histórico de conversas em **texto limpo e legível**.

O foco não é velocidade: é **ENTENDER** o que cada peça faz. Vá com calma, leia
os comentários e rode um passo de cada vez.

## O que você vai construir

Um agente de terminal que:
- conversa com você em português;
- **lembra** do que já foi dito (memória persistente no banco);
- **decide sozinho** quando buscar na web (ferramenta Tavily);
- **salva** cada pergunta e resposta em tabelas que você consegue ler.

## Índice

- [Vocabulário mínimo (leia primeiro)](#vocabulário-mínimo-leia-primeiro)
- [PARTE 1 — Instalar o PostgreSQL no Windows](#parte-1--instalar-o-postgresql-no-windows)
- [Preparar o projeto Python com uv](#preparar-o-projeto-python-com-uv)
- [PARTE 2 — O agente, em ordem crescente de complexidade](#parte-2--o-agente-em-ordem-crescente-de-complexidade)
- [PARTE 3 — Ver as conversas de forma legível](#parte-3--ver-as-conversas-de-forma-legível)
- [Segurança (obrigatório)](#segurança-obrigatório)
- [Preparado para o futuro](#preparado-para-o-futuro)
- [Versionamento com Git (por último)](#versionamento-com-git-por-último)

---

## Vocabulário mínimo (leia primeiro)

Antes do código, cinco palavras que vão aparecer o tempo todo:

- **LLM (modelo de linguagem)**: o "cérebro" que lê texto e escreve texto. Aqui
  usamos o `gpt-3.5-turbo` da OpenAI.
- **Prompt**: o texto de instrução que você manda ao modelo.
- **Chain (corrente)**: uma sequência de peças ligadas, onde a saída de uma é a
  entrada da próxima (prompt → modelo → parser).
- **Agent (agente)**: um modelo que, além de responder, pode **decidir usar
  ferramentas** (buscar na web, calcular, etc.) antes de dar a resposta final.
- **Tool (ferramenta)**: uma função que o agente pode chamar sozinho quando
  julgar necessário.
- **Checkpointer**: o componente do LangGraph que **salva a memória** do agente
  (o histórico) para que ele lembre da conversa mesmo depois de fechar o programa.

---

## PARTE 1 — Instalar o PostgreSQL no Windows

O **PostgreSQL** é o banco de dados onde vamos guardar a memória do agente e o
histórico de conversas. Vamos instalar tudo pelo terminal **PowerShell**.

> Abra o PowerShell: tecla Windows → digite `PowerShell` → Enter.

### 1.1 Verificar se o PostgreSQL já está instalado

Antes de instalar, cheque se já existe. Dois testes:

```powershell
Get-Service -Name postgresql*
```

- `Get-Service` lista os **serviços** do Windows (programas que rodam em segundo
  plano). O `postgresql*` filtra só os que começam com "postgresql".
- Se **não aparecer nada**, provavelmente não está instalado.
- Se aparecer algo com `Status: Running`, já está instalado e rodando.

E confira se a pasta de instalação existe:

```powershell
Test-Path "C:\Program Files\PostgreSQL"
```

- `Test-Path` responde `True` (existe) ou `False` (não existe) para um caminho.
- `True` = já instalado. `False` = precisamos instalar.

### 1.2 Instalar via winget

O `winget` é o instalador de programas oficial do Windows (linha de comando).

```powershell
winget install PostgreSQL.PostgreSQL.18
```

- `winget install` baixa e instala um programa pelo seu identificador.
- `PostgreSQL.PostgreSQL.18` é o identificador da versão 18 do PostgreSQL.
- Durante a instalação, **anote a senha** do usuário `postgres` (o
  administrador do banco). Você vai precisar dela o tempo todo. Se o instalador
  gráfico abrir, aceite a **porta padrão 5432**.

> Não lembra a senha depois? Sem problema por enquanto — ela vai para o `.env`.

### 1.3 Adicionar o `psql` ao PATH do Windows

O `psql` é o programa de terminal que conversa com o banco. Ele fica dentro da
pasta `bin` do PostgreSQL, mas o Windows ainda não sabe onde procurá-lo. O
**PATH** é a lista de pastas onde o Windows procura programas. Vamos adicionar a
pasta `bin` a essa lista:

```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\PostgreSQL\18\bin", "User")
```

Explicando o comando por partes:
- `[Environment]::SetEnvironmentVariable(...)` altera uma variável de ambiente.
- `"Path"` é a variável que estamos mudando (o PATH).
- `$env:Path + ";C:\Program Files\PostgreSQL\18\bin"` pega o PATH atual e
  **acrescenta** (o `+`) a pasta `bin`. O `;` separa uma pasta da outra.
- `"User"` significa aplicar só ao **seu usuário** (não precisa de admin).

> Se você instalou uma versão diferente da 18, troque o número `18` na pasta.

### 1.4 Reabrir o terminal (importante!)

O PATH só é lido **quando o terminal abre**. Então a mudança acima **não vale**
no terminal atual. **Feche completamente o PowerShell e abra de novo.** Depois,
teste:

```powershell
psql --version
```

- Se aparecer algo como `psql (PostgreSQL) 18.x`, o PATH funcionou. 🎉
- Se disser "não é reconhecido", o terminal não foi reaberto ou o caminho da
  pasta `bin` está diferente — confira a versão instalada.

### 1.5 Confirmar que o serviço está rodando

```powershell
Get-Service -Name postgresql*
```

- Procure a coluna `Status`. Precisa estar **`Running`**.
- Se estiver `Stopped`, inicie com (pode pedir permissão de administrador):

```powershell
Start-Service postgresql-x64-18
```

### 1.6 Conectar com o `psql`

```powershell
psql -U postgres
```

- `-U postgres` diz "conectar como o usuário **postgres**" (o administrador).
- Ele vai pedir a **senha**. ATENÇÃO: você digita **às cegas** — a senha **não
  aparece na tela** (nem asteriscos). Isso é normal e proposital. Digite a senha
  e aperte Enter.
- Deu certo? O prompt muda para `postgres=#`. Você está **dentro do banco**.

### 1.7 Criar o banco de dados do projeto

Já dentro do `psql` (com o prompt `postgres=#`), crie o banco:

```sql
CREATE DATABASE agente_ia;
```

- `CREATE DATABASE` cria um banco novo.
- `agente_ia` é o nome que escolhemos (é o mesmo do `.env.example`).
- **Não esqueça o `;` no final** — no `psql`, o comando só executa quando você
  fecha com ponto e vírgula.

Confira que o banco foi criado listando todos:

```sql
\l
```

- `\l` (letra ele minúscula) lista todos os bancos. Você deve ver `agente_ia`.

Para sair do `psql` e voltar ao PowerShell:

```sql
\q
```

- `\q` = **quit** (sair).

**Pronto! A Parte 1 está concluída.** Você tem o PostgreSQL instalado, rodando,
o `psql` no PATH e o banco `agente_ia` criado.

---

## Preparar o projeto Python com uv

O **`uv`** é um gerenciador de projetos Python moderno e rápido. Ele cria o
ambiente virtual (uma "caixa" isolada com as bibliotecas do projeto) e instala
as dependências.

### 2.0.1 Instalar o uv (se ainda não tiver)

```powershell
winget install astral-sh.uv
```

Reabra o terminal e confira:

```powershell
uv --version
```

### 2.0.2 Entrar na pasta do projeto

No PowerShell, navegue até a pasta deste projeto (ajuste o caminho se o seu for
diferente):

```powershell
cd "C:\Users\renan\OneDrive\Tudo\Trabalho\Desenvolvimento\PROJETO NOVO - Python\Arquivos de um Projeto Novo\LangChain1.0"
```

- `cd` = **change directory** (mudar de pasta). As aspas são necessárias porque
  o caminho tem espaços.

### 2.0.3 Instalar as dependências

O arquivo [`pyproject.toml`](pyproject.toml) já lista tudo o que precisamos.
Basta um comando:

```powershell
uv sync
```

- `uv sync` lê o `pyproject.toml`, cria a pasta `.venv` (o ambiente isolado) e
  baixa **todas** as bibliotecas listadas. Pode demorar um pouco na 1ª vez.

> ⚠️ **Deu erro "os error 396"? Use `uv sync --link-mode=copy`.** Se a pasta do
> projeto for gerenciada por uma **sincronização em nuvem** (OneDrive, Google
> Drive, Dropbox…), o `uv sync` normal pode FALHAR com *"A operação de nuvem não
> pode ser executada... links físicos incompatíveis (os error 396)"*. Motivo: o
> `uv` usa *hardlinks* por padrão, e esses sincronizadores não suportam. A
> correção é mandar o `uv` **copiar** em vez de "linkar":
>
> ```powershell
> uv sync --link-mode=copy
> ```
>
> Para não digitar isso toda vez, configure de uma vez (e reabra o terminal):
> `setx UV_LINK_MODE copy`. **Melhor ainda:** mantenha projetos Python **fora** de
> qualquer pasta sincronizada (ex.: `C:\Projetos\...`, na raiz do disco) — evita
> esse erro e a sincronização constante da `.venv`. Veja mais em
> [Problemas comuns no Windows](#problemas-comuns-no-windows).

### 2.0.4 Criar o seu `.env` a partir do modelo

```powershell
Copy-Item .env.example .env
```

- `Copy-Item` copia um arquivo. Aqui, criamos o `.env` a partir do modelo.
- **Agora abra o `.env` no VS Code** e preencha os valores reais: suas chaves de
  API e a senha do PostgreSQL na `DATABASE_URL`. O `.env` **nunca** vai para o
  GitHub (está no `.gitignore`).

> Como rodar qualquer script depois: use `uv run python agent.py`. O `uv run`
> executa o comando **dentro** do ambiente virtual do projeto, com as
> bibliotecas certas. Não precisa "ativar" a `.venv` manualmente.

---

## PARTE 2 — O agente, em ordem crescente de complexidade

Aqui a gente monta o agente **em camadas**, do mais simples ao completo. Os
trechos abaixo são para você **entender cada conceito**. A versão final e
funcional, com tudo junto, está no arquivo [`agent.py`](agent.py).

### 2.1 A estrutura base: prompt → model → parser (a "chain")

A menor unidade útil do LangChain é uma **chain** (corrente): três peças ligadas
em sequência. Pense numa linha de montagem:

1. **Prompt** — monta o texto de instrução (com espaços a preencher).
2. **Model** — o LLM, que recebe o texto e gera uma resposta.
3. **Parser** — pega a resposta do modelo e a transforma no formato que queremos
   (aqui, texto puro).

O operador que liga as peças é o **`|`** (barra vertical, "pipe"). Ele significa:
"pegue a saída da esquerda e entregue como entrada para a direita". É o mesmo
espírito do "cano" do terminal.

```python
from langchain_openai import ChatOpenAI                     # o conector do modelo OpenAI
from langchain_core.prompts import ChatPromptTemplate       # monta prompts com "buracos" a preencher
from langchain_core.output_parsers import StrOutputParser   # transforma a resposta em texto puro
from dotenv import load_dotenv                              # carrega os segredos do .env

load_dotenv()                                               # lê o .env (pega a OPENAI_API_KEY)

# 1) PROMPT: um molde de conversa. {pergunta} é um "buraco" preenchido depois.
prompt = ChatPromptTemplate.from_messages([                 # cria o molde a partir de uma lista de mensagens
    ("system", "Você é um assistente que responde em português."),  # instrução fixa (personalidade)
    ("user", "{pergunta}"),                                 # a fala do usuário; {pergunta} será substituído
])

# 2) MODEL: o cérebro. temperature=0 = respostas mais objetivas e previsíveis.
model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)    # cria o objeto do modelo (usa a chave do .env)

# 3) PARSER: converte o objeto de resposta do modelo em uma string simples.
parser = StrOutputParser()                                  # o "tradutor" da saída para texto puro

# LIGANDO AS PEÇAS COM | :  prompt -> model -> parser
chain = prompt | model | parser                             # cria a chain (a linha de montagem)

# invoke() "roda" a chain. Passamos um dicionário preenchendo o {pergunta}.
resposta = chain.invoke({"pergunta": "Explique o que é uma API em uma frase."})
print(resposta)                                             # mostra o texto final na tela
```

**O que aconteceu:** o dicionário `{"pergunta": ...}` preencheu o buraco do
prompt; o texto pronto foi para o `model`; a resposta do `model` foi para o
`parser`; e o `parser` devolveu uma string. Essa é a base de tudo.

### 2.2 De chain para agente: `create_agent` + `system_prompt`

Uma chain sempre faz a **mesma** sequência. Um **agente** é mais esperto: ele
pode **decidir** usar ferramentas antes de responder. No LangChain 1.0, a função
que monta um agente pronto é a `create_agent`.

O `system_prompt` aqui tem o mesmo papel do "system" da chain: são as
**instruções permanentes** — quem o agente é e como se comporta.

```python
from langchain.agents import create_agent                  # a função que cria o agente
from dotenv import load_dotenv                             # carrega os segredos

load_dotenv()                                              # lê o .env

# system_prompt = a personalidade/instruções permanentes do agente.
system_prompt = "Você é um assistente prestativo que responde em português."

# create_agent monta o agente. Por enquanto, SEM ferramentas (tools=[]).
agente = create_agent(                                     # cria o agente
    model="openai:gpt-3.5-turbo",                          # modelo no formato "provedor:modelo"
    tools=[],                                              # lista de ferramentas (vazia por ora)
    system_prompt=system_prompt,                           # a personalidade
)

# invoke espera um dicionário com "messages": uma lista de mensagens {role, content}.
resultado = agente.invoke(                                 # roda o agente
    {"messages": [{"role": "user", "content": "Quanto é 2 + 2?"}]}  # a pergunta do usuário
)

# A resposta final é a ÚLTIMA mensagem da lista ([-1]); .content é o texto dela.
print(resultado["messages"][-1].content)                   # imprime a resposta
```

> Para trocar de modelo depois, basta mudar a string: `"google_genai:gemini-1.5-flash"`
> (e ter a `GOOGLE_API_KEY` no `.env`). O resto do código continua igual.

### 2.3 Memória persistente com `PostgresSaver` (o checkpointer)

Até aqui, o agente **esquece** tudo quando o programa termina. Para ele
**lembrar**, usamos um **checkpointer**: o componente do LangGraph que salva o
estado da conversa. Vamos salvar no PostgreSQL com o `PostgresSaver`.

> 💡 **Dica de aprendizado (o caminho que funciona melhor):** antes de configurar
> o PostgreSQL, comece com uma memória **na RAM** para entender o conceito sem
> nenhuma infraestrutura. Use `from langgraph.checkpoint.memory import InMemorySaver`
> e `checkpointer = InMemorySaver()` (sem `.setup()` e sem `with`). O agente já
> passa a lembrar **dentro da mesma execução** — teste dizendo seu nome e
> perguntando em seguida. Depois, ao trocar para o `PostgresSaver`, a memória passa
> a **sobreviver a fechar e reabrir** o programa. Assim você sente na prática a
> diferença entre "memória na RAM" (some ao fechar) e "memória persistente" (fica
> no banco).

Dois conceitos novos:

- **O bloco `with`**: o `PostgresSaver` abre uma conexão com o banco que precisa
  ser **fechada corretamente** no fim. O `with` cuida disso automaticamente:
  abre no começo do bloco e fecha ao sair, **mesmo se der erro** no meio. É a
  forma segura de lidar com recursos (conexões, arquivos).
- **`checkpointer.setup()`**: na **primeira** vez, o LangGraph precisa criar as
  tabelas internas dele (como `checkpoints`) dentro do banco. O `setup()` faz
  isso. É seguro chamar sempre: se as tabelas já existem, ele apenas confere.

```python
import os                                                  # para ler variáveis de ambiente
from langchain.agents import create_agent                  # cria o agente
from langgraph.checkpoint.postgres import PostgresSaver    # o checkpointer que salva no PostgreSQL
from dotenv import load_dotenv                             # carrega os segredos

load_dotenv()                                              # lê o .env
DATABASE_URL = os.environ["DATABASE_URL"]                  # pega a URL do banco do .env

# Abrimos o checkpointer dentro de um `with` (abre/fecha a conexão com segurança).
with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:  # conecta ao banco
    checkpointer.setup()                                   # cria as tabelas internas (só na 1ª vez importa)

    # Passamos o checkpointer ao agente: agora ele tem MEMÓRIA.
    agente = create_agent(                                 # cria o agente com memória
        model="openai:gpt-3.5-turbo",                      # o modelo
        tools=[],                                          # ainda sem ferramentas
        system_prompt="Você responde em português.",       # personalidade
        checkpointer=checkpointer,                         # <- a memória persistente
    )

    # O thread_id identifica a conversa. Mesmo id = mesma memória.
    config = {"configurable": {"thread_id": "conversa-1"}} # diz ao agente QUAL conversa é esta

    # Primeira mensagem: apresentamos um nome.
    r1 = agente.invoke(                                    # roda o agente
        {"messages": [{"role": "user", "content": "Meu nome é Renan."}]},  # 1ª pergunta
        config,                                            # com o thread_id
    )
    print(r1["messages"][-1].content)                      # resposta 1

    # Segunda mensagem: testamos se ele LEMBRA (mesmo thread_id).
    r2 = agente.invoke(                                    # roda de novo
        {"messages": [{"role": "user", "content": "Qual é o meu nome?"}]},  # 2ª pergunta
        config,                                            # MESMO thread_id -> ele lembra
    )
    print(r2["messages"][-1].content)                      # deve responder "Renan"
```

Se ele responder "Renan" na segunda pergunta, a **memória** está funcionando —
e ela ficou salva no banco, não só na memória do programa.

### 2.4 Uma ferramenta (tool) de busca na web: Tavily

O `gpt-3.5-turbo` não conhece fatos **atuais** (ele foi treinado até certa
data). Uma **tool** resolve isso: damos ao agente a ferramenta **Tavily**, que
faz buscas na web. O importante: **o agente decide sozinho** quando usá-la.
Pergunta simples ("2+2") ele responde direto; pergunta atual ("cotação do dólar
hoje") ele **escolhe** chamar a busca.

Como ele decide? Cada tool tem uma **descrição**. O modelo lê a sua pergunta,
compara com as descrições das tools disponíveis e decide se — e qual — usar.

```python
import os                                                  # variáveis de ambiente
from langchain.agents import create_agent                  # cria o agente
from langchain_tavily import TavilySearch                  # a ferramenta de busca na web
from langgraph.checkpoint.postgres import PostgresSaver    # o checkpointer
from dotenv import load_dotenv                             # carrega segredos

load_dotenv()                                              # lê o .env (pega TAVILY_API_KEY e DATABASE_URL)
DATABASE_URL = os.environ["DATABASE_URL"]                  # URL do banco

busca_web = TavilySearch(max_results=3)                    # cria a tool; traz até 3 resultados por busca

with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:  # abre o checkpointer
    checkpointer.setup()                                   # garante as tabelas internas

    agente = create_agent(                                 # cria o agente...
        model="openai:gpt-3.5-turbo",                      # modelo
        tools=[busca_web],                                 # ...agora COM a ferramenta de busca
        system_prompt="Responda em português. Use a busca quando precisar de fatos atuais.",
        checkpointer=checkpointer,                         # memória
    )

    config = {"configurable": {"thread_id": "conversa-1"}} # identificador da conversa

    # Uma pergunta ATUAL: o agente provavelmente vai DECIDIR usar a busca.
    r = agente.invoke(                                     # roda o agente
        {"messages": [{"role": "user", "content": "Quais as notícias de tecnologia hoje?"}]},
        config,
    )
    print(r["messages"][-1].content)                       # resposta (já com dados da web)
```

### 2.5 O loop de conversa pelo terminal

Até agora perguntamos "no braço", uma linha por vez. Um **loop** deixa você
conversar continuamente: o programa pergunta, você digita, ele responde, e
repete — até você digitar `sair`.

```python
while True:                                                # repete "para sempre" (até um break)
    pergunta = input("Você: ")                             # mostra "Você: " e espera você digitar + Enter
    if pergunta.strip().lower() == "sair":                 # se você digitou "sair" (ignorando espaços/maiúsculas)
        break                                              # break = sai do while, encerra o loop
    resultado = agente.invoke(                             # manda sua pergunta ao agente
        {"messages": [{"role": "user", "content": pergunta}]},
        config,
    )
    print("Agente:", resultado["messages"][-1].content)    # imprime a resposta do agente
```

Junte 2.1 → 2.5 e você tem o agente completo. **Tudo isso já está montado,
comentado linha a linha, no arquivo [`agent.py`](agent.py)** — inclusive a parte
de salvar o histórico (Parte 3). Para rodar:

```powershell
uv run python agent.py
```

### 2.6 Controle de memória (resumir conversas longas)

#### O que é a "janela de contexto" e por que conversa longa é um problema

O modelo **não tem memória própria**. A cada mensagem sua, o programa reenvia
**todo o histórico** da conversa junto — é assim que ele "lembra". Mas todo
modelo tem um limite de quanto texto consegue ler de uma vez, chamado **janela
de contexto** (medida em **tokens** — pedaços de palavra; grosso modo, ~4
caracteres = 1 token).

Numa conversa longa, o histórico cresce sem parar. Isso traz três problemas:

1. **Estouro**: se o histórico passar da janela de contexto, o modelo dá erro.
2. **Custo**: você paga por token enviado; histórico gigante = conta alta.
3. **Lentidão**: mais texto para ler = resposta mais lenta.

#### O que o middleware faz

Um **middleware** é um "meio de campo": um componente que fica **entre** você e
o modelo e pode agir automaticamente a cada rodada. O
**`SummarizationMiddleware`** vigia o tamanho do histórico e, quando ele passa
de um limite, **resume** as mensagens antigas em um texto curto (usando o próprio
modelo para escrever o resumo) e continua a conversa com esse resumo no lugar do
histórico gigante. Você não perde o "fio da meada", mas gasta muito menos espaço.

#### Resumir por tokens ou por número de mensagens?

Nós deixamos **as duas estratégias no código** ao mesmo tempo; você escolhe pelo
`.env` (sem mexer no código):

- **Por tokens** (padrão, recomendado): resume quando o histórico passa de X
  **tokens**. É a medida "real" que o modelo usa, então protege melhor contra o
  estouro. Desvantagem: token é uma unidade menos intuitiva para humanos.
- **Por mensagens** (alternativa): resume quando passam de N **mensagens**
  (perguntas + respostas). É fácil de entender ("resuma a cada 40 mensagens"),
  mas menos preciso — 40 mensagens curtas ocupam muito menos que 40 longas.

> **Nota técnica (verificada na biblioteca instalada):** na versão atual do
> LangChain, o `SummarizationMiddleware` usa **um único parâmetro `trigger`**,
> que recebe uma tupla `(tipo, limite)` — `("tokens", 3000)` ou
> `("messages", 40)`. Tutoriais antigos citam parâmetros separados como
> `max_tokens_before_summary`; **isso mudou**. O nosso `if/elif` monta a tupla
> `trigger` certa conforme a estratégia. Existe também o parâmetro `keep`
> (padrão: manter as 20 mensagens mais recentes intactas após o resumo).

#### `trigger` × `keep` (a pegadinha mais comum) ⚠️

São **dois** parâmetros independentes, e confundir os dois é o erro nº 1:

- **`trigger`** = *QUANDO* resumir (o gatilho). Ex.: `("tokens", 2000)`.
- **`keep`** = *QUANTO* manter intacto **depois** de resumir. Padrão: `("messages", 20)`.

A pegadinha: se o `keep` for **maior** que o histórico atual, o `trigger` até dispara,
mas **não sobra nada para resumir** — nenhum resumo é gerado. Ex.: `trigger=("messages", 6)`
com o `keep` padrão de 20 → dispara aos 7, mas manda manter 20, então mantém tudo e
não compacta nada.

**Regra de ouro:** o `keep` tem que ser **bem menor** que o `trigger`, e o ideal é
deixar os dois na **mesma unidade**:

```python
SummarizationMiddleware(
    model="openai:gpt-3.5-turbo",
    trigger=("tokens", 2000),   # resume quando passar de 2000 tokens
    keep=("tokens", 500),       # mantém ~500 tokens recentes; o resto vira resumo
)
```

Para **forçar** o resumo em um teste (poucas mensagens), use algo como
`trigger=("messages", 6)` **junto com** `keep=("messages", 2)`.

#### Onde VER o resumo gerado

O resumo é inserido no histórico como uma mensagem cujo conteúdo começa com
*"Here is a summary of the conversation to date:"* e fica salvo (em `jsonb`) na
tabela `checkpoints`. As formas práticas de vê-lo:
- **LangSmith:** o trace mostra o passo de sumarização e o texto gerado.
- **Uma tabela própria `resumos`:** no loop, após o `invoke`, procure a mensagem
  com aquele prefixo em `resultado["messages"]` e salve-a (com `ON CONFLICT` no
  `mensagem_id` para não duplicar). Assim você lê os resumos em texto limpo.

#### Como eu troco de estratégia (editando só o `.env`)

Três variáveis no [`.env`](.env.example) controlam tudo (todas opcionais — se
faltarem, o código usa padrões):

```bash
ESTRATEGIA_MEMORIA=tokens     # "tokens" (padrão) ou "mensagens"
MAX_TOKENS_RESUMO=3000        # usado quando a estratégia é "tokens"
MAX_MENSAGENS_RESUMO=40       # usado quando a estratégia é "mensagens"
```

- Para usar a alternativa, mude **só** a primeira linha para
  `ESTRATEGIA_MEMORIA=mensagens` e salve. Nada de mexer no `.py`.
- Os valores numéricos chegam como **texto** do `.env`; no código eles são
  convertidos para número inteiro com `int(...)` (por isso funcionam nas contas).

No [`agent.py`](agent.py), o trecho que faz a escolha é o **bloco 6.1b**:

```python
if ESTRATEGIA_MEMORIA == "tokens":                # estratégia principal
    gatilho = ("tokens", MAX_TOKENS_RESUMO)       # tupla (tipo, limite)
elif ESTRATEGIA_MEMORIA == "mensagens":           # estratégia alternativa
    gatilho = ("messages", MAX_MENSAGENS_RESUMO)  # note o "messages" em inglês
else:                                             # valor inválido -> padrão seguro
    gatilho = ("tokens", MAX_TOKENS_RESUMO)

memoria_middleware = SummarizationMiddleware(     # cria o middleware
    model=modelo,                                 # usa o MESMO modelo do agente
    trigger=gatilho,                              # a regra de quando resumir
)
```

E ele entra no agente pelo parâmetro `middleware=[memoria_middleware]` do
`create_agent`.

---

## PARTE 3 — Ver as conversas de forma legível

### 3.1 O problema

O LangGraph salva a memória nas tabelas internas dele (principalmente
`checkpoints`), em formato **`jsonb`** — um JSON binário ótimo para a máquina,
mas **ilegível** para humanos. Se você abrir essa tabela, vai ver blocos enormes
e confusos.

**Solução:** criar as **nossas próprias tabelas** (`conversas` e `mensagens`),
onde salvamos cada pergunta e resposta em **texto puro**, prontas para ler.

### 3.2 As duas tabelas (relação um-para-muitos)

Vamos ter duas tabelas ligadas:

- `conversas` — uma linha por conversa.
- `mensagens` — várias linhas por conversa (cada pergunta e cada resposta).

A ligação **um-para-muitos** ("uma conversa tem muitas mensagens") é feita por
uma **chave estrangeira** (foreign key): a mensagem guarda o `id` da conversa
dona dela. Conceitos que aparecem no SQL:

- **`SERIAL`** — número inteiro que o banco **autoincrementa** sozinho (1, 2,
  3...). Perfeito para `id`, você nunca precisa informar.
- **`PRIMARY KEY`** (chave primária) — o identificador único e oficial da linha.
  Não repete e não pode ser vazio.
- **`REFERENCES`** — cria a **chave estrangeira**: obriga o valor a existir na
  outra tabela. É o que garante a relação e a integridade dos dados.
- **`TIMESTAMP DEFAULT NOW()`** — coluna de data/hora que, se você não informar,
  o banco preenche com o **momento atual** automaticamente.
- **`UNIQUE`** — proíbe valores repetidos na coluna. Usamos no `thread_id` para
  garantir **uma** linha por conversa (e é isso que faz o `ON CONFLICT` do
  Python funcionar).

O SQL completo (e comentado) está em
[`sql/criar_tabelas.sql`](sql/criar_tabelas.sql). Resumo:

```sql
CREATE TABLE IF NOT EXISTS conversas (
    id SERIAL PRIMARY KEY,             -- id único, autoincrementado
    thread_id TEXT UNIQUE NOT NULL,    -- código da conversa; UNIQUE = sem repetir
    titulo TEXT,                       -- nome amigável opcional
    criada_em TIMESTAMP DEFAULT NOW()  -- data/hora automática de criação
);

CREATE TABLE IF NOT EXISTS mensagens (
    id SERIAL PRIMARY KEY,                              -- id da mensagem
    conversa_id INTEGER NOT NULL REFERENCES conversas(id),  -- chave estrangeira -> conversas.id
    papel TEXT NOT NULL,                               -- 'user' ou 'assistant'
    conteudo TEXT NOT NULL,                            -- o texto da mensagem
    criada_em TIMESTAMP DEFAULT NOW()                  -- data/hora automática
);
```

**Como criar essas tabelas:** conecte no banco certo e rode o arquivo. No
PowerShell:

```powershell
psql -U postgres -d agente_ia -f sql\criar_tabelas.sql
```

- `-d agente_ia` = conecta **no banco** `agente_ia` (não no banco padrão!).
- `-f sql\criar_tabelas.sql` = executa o **arquivo** SQL indicado.

### 3.3 Função `garantir_conversa` (cria a conversa e devolve o id)

No começo de cada sessão, garantimos que exista uma linha em `conversas` para o
`thread_id` atual, e pegamos o `id` dela. O truque é o **`RETURNING id`**: ao
inserir, pedimos ao banco para **devolver** o id recém-criado (assim não
precisamos de uma segunda consulta no caso normal).

```python
def garantir_conversa(conn, thread_id):                   # recebe a conexão e o código da conversa
    with conn.cursor() as cur:                            # abre um cursor (canal de comandos SQL)
        cur.execute(                                      # executa o comando abaixo
            """
            INSERT INTO conversas (thread_id)             -- tenta inserir a conversa
            VALUES (%s)                                   -- o valor entra via %s (seguro)
            ON CONFLICT (thread_id) DO NOTHING            -- se já existir (UNIQUE), não faz nada
            RETURNING id                                  -- devolve o id inserido
            """,
            (thread_id,),                                 # o valor que substitui o %s (uma tupla)
        )
        linha = cur.fetchone()                            # pega a linha devolvida (ou None)
        if linha is not None:                             # se veio algo, a inserção aconteceu
            conversa_id = linha[0]                         # o id está na posição 0
        else:                                             # senão, a conversa já existia (ON CONFLICT pulou)
            cur.execute(                                  # buscamos o id que já está lá
                "SELECT id FROM conversas WHERE thread_id = %s",
                (thread_id,),
            )
            conversa_id = cur.fetchone()[0]               # pega o id existente
    conn.commit()                                         # confirma (grava) no banco
    return conversa_id                                    # devolve o id para quem chamou
```

### 3.4 Função `salvar_mensagem` (queries parametrizadas com `%s`)

Cada mensagem é inserida com **query parametrizada** (`%s`). Isso é uma **regra
de segurança**, não um detalhe:

> **Por que NÃO usar f-string aqui?** Se montássemos o SQL com f-string, como
> `f"INSERT ... VALUES ('{conteudo}')"`, e o texto contivesse aspas ou comandos,
> um usuário mal-intencionado poderia **injetar comandos SQL** (isso se chama
> **SQL injection**) e apagar ou roubar dados. Com `%s`, o driver `psycopg`
> trata o valor **sempre como dado puro**, nunca como comando. **Sempre `%s`.**

```python
def salvar_mensagem(conn, conversa_id, papel, conteudo):  # conexão, id da conversa, papel, texto
    with conn.cursor() as cur:                            # abre o cursor
        cur.execute(                                      # executa a inserção
            "INSERT INTO mensagens (conversa_id, papel, conteudo) VALUES (%s, %s, %s)",  # 3 buracos %s
            (conversa_id, papel, conteudo),               # os 3 valores, na ordem (query parametrizada)
        )
    conn.commit()                                         # confirma a gravação
```

### 3.5 Chamando as funções dentro do loop

No loop de conversa, salvamos **duas** mensagens por rodada: a sua pergunta
(papel `'user'`) e a resposta do agente (papel `'assistant'`).

```python
conversa_id = garantir_conversa(conn, thread_id)          # 1x no início: garante a conversa e pega o id

while True:                                               # loop de conversa
    pergunta = input("Você: ")                            # lê o que você digitou
    if pergunta.strip().lower() == "sair":                # comando de saída
        break                                             # encerra o loop
    salvar_mensagem(conn, conversa_id, "user", pergunta)  # salva a SUA pergunta (papel 'user')
    resultado = agente.invoke(                            # pergunta ao agente
        {"messages": [{"role": "user", "content": pergunta}]},
        config,
    )
    resposta = resultado["messages"][-1].content          # extrai o texto da resposta
    salvar_mensagem(conn, conversa_id, "assistant", resposta)  # salva a RESPOSTA (papel 'assistant')
    print("Agente:", resposta)                            # mostra na tela
```

> Tudo isso já está no [`agent.py`](agent.py), integrado e comentado.

### 3.6 A consulta com JOIN (ver a conversa em texto)

Para ler o histórico, juntamos as duas tabelas com um **JOIN** (juntar) e
ordenamos por data. O arquivo pronto é
[`sql/consultar_conversas.sql`](sql/consultar_conversas.sql):

```sql
SELECT
    c.thread_id AS conversa,     -- coluna vinda da tabela conversas (apelido "c")
    m.papel     AS quem_falou,   -- 'user' ou 'assistant' (tabela mensagens, apelido "m")
    m.conteudo  AS mensagem,     -- o texto
    m.criada_em AS quando        -- a data/hora
FROM mensagens AS m              -- tabela principal: mensagens (apelidada "m")
JOIN conversas AS c              -- juntamos com conversas (apelidada "c")
    ON m.conversa_id = c.id      -- REGRA do JOIN: mensagem.conversa_id = conversa.id
ORDER BY m.criada_em ASC;        -- ordena do mais antigo ao mais novo
```

Lendo o JOIN linha a linha:
- `FROM mensagens AS m` — começamos pela tabela de mensagens; `AS m` é um apelido
  curto para não escrever "mensagens." toda hora.
- `JOIN conversas AS c` — pedimos para **juntar** cada mensagem com a sua
  conversa; `c` é o apelido de `conversas`.
- `ON m.conversa_id = c.id` — a **condição** que casa as linhas: pegue a conversa
  cujo `id` seja igual ao `conversa_id` guardado na mensagem. É a chave
  estrangeira em ação.
- `ORDER BY m.criada_em ASC` — ordena por data/hora crescente (`ASC`), para ler
  de cima para baixo na ordem em que a conversa aconteceu.

### 3.7 Como rodar a consulta no pgAdmin (abrindo no banco CERTO)

O **pgAdmin** é a interface gráfica do PostgreSQL (instala junto). O erro mais
comum de iniciante é abrir o Query Tool **no banco errado** e não achar as
tabelas. Faça exatamente assim:

1. Abra o **pgAdmin** (menu Iniciar → pgAdmin).
2. Na árvore à esquerda, expanda: **Servers → PostgreSQL 18** (digite a senha do
   `postgres` se pedir).
3. Expanda **Databases**. Você verá vários bancos. **Clique em `agente_ia`** —
   este é o banco do projeto. (Se clicar em `postgres`, é o banco errado e as
   tabelas não vão aparecer!)
4. Com `agente_ia` **selecionado** (destacado), clique com o botão direito nele
   → **Query Tool**. Uma janela de consulta abre **conectada ao banco certo**.
5. Cole o SQL do JOIN (da seção 3.6) e clique no botão **▶ (Execute/Run)** ou
   aperte **F5**.
6. O resultado aparece embaixo, em formato de tabela: coluna `quem_falou`,
   `mensagem`, `quando` — a sua conversa em **texto limpo**. 🎉

> Dica: para confirmar em qual banco você está, olhe o topo da janela do Query
> Tool — ele mostra `agente_ia/postgres@PostgreSQL 18`. Se aparecer
> `postgres/postgres@...`, você abriu no banco errado; feche e repita o passo 3.

---

## PARTE 4 — Ver o agente "por dentro" (LangSmith e LangGraph Studio)

Até aqui você lê as conversas no banco (texto). Mas como **entender o raciocínio**
do agente — qual tool ele decidiu chamar, o que ela respondeu, quantos tokens
gastou? Para isso existem duas ferramentas visuais. Elas são **opcionais**, mas
excelentes para quem está aprendendo.

### 4.1 LangSmith — o "raio-x" da conversa (painel na web)

O **LangSmith** grava cada passo do agente e mostra num painel online: o prompt
enviado ao modelo, cada chamada de tool com entrada/saída, tokens, tempo e custo.
É como ver o "filme" do que aconteceu por dentro de cada resposta.

**O melhor:** você **não muda uma linha de código**. O LangChain manda os dados
sozinho quando encontra as variáveis certas no `.env`. Basta preencher:

```bash
LANGSMITH_TRACING=true                          # liga o rastreamento
LANGSMITH_API_KEY=coloque-sua-chave-langsmith   # sua chave (só no .env)
LANGSMITH_PROJECT=langchain1-estudo             # nome do projeto no painel
```

Passo a passo:
1. Crie conta em https://smith.langchain.com/ e gere uma **API key** (em Settings).
2. Cole as três variáveis acima no seu `.env` (elas já estão no `.env.example`).
3. Rode o agente normalmente: `uv run python agent.py` e converse.
4. Volte ao site do LangSmith → seu projeto `langchain1-estudo`. Cada mensagem
   vira um **trace**: clique para abrir e navegar passo a passo (prompt → decisão
   de tool → resultado → resposta). É aqui que você "vê" o agente pensando.

> Por que não precisa de código? Porque o LangChain checa essas variáveis de
> ambiente automaticamente. Sem `LANGSMITH_TRACING=true`, nada é enviado — então
> é seguro deixar desligado quando não quiser rastrear.

### 4.2 LangGraph Studio — o grafo visual (e o `langgraph.json`)

O **LangGraph Studio** é um painel LOCAL onde você **vê o grafo do agente
desenhado** (os nós, as ligações) e pode **executá-lo pela interface**, sem o
terminal. Para ele funcionar, o LangGraph precisa de um arquivo de configuração
na raiz do projeto: o **`langgraph.json`**.

O nosso [`langgraph.json`](langgraph.json):

```json
{
    "dependencies": ["."],
    "graphs": {
        "agente": "./agent.py:criar_grafo"
    },
    "env": ".env"
}
```

Campo a campo:
- **`dependencies`**: onde estão as dependências do projeto. `["."]` = "a pasta
  atual" (o LangGraph usa o `pyproject.toml`/`uv` daqui).
- **`graphs`**: o mapa de grafos que o Studio vai mostrar. A chave `"agente"` é
  o nome que aparece no painel; o valor `"./agent.py:criar_grafo"` diz
  **arquivo:função** — "no `agent.py`, chame a função `criar_grafo`".
- **`env`**: qual arquivo de segredos carregar. Apontamos para o `.env`.

**Por que `criar_grafo` e não o agente do `main()`?** Porque o Studio precisa
importar o grafo "de fora", e o agente do `main()` é montado dentro de uma
função (o Studio não alcança). Por isso criamos, no `agent.py`, uma **fábrica**
de grafo no nível do módulo:

```python
def construir_agente(checkpointer=None):   # monta o agente (reusado pelo terminal e Studio)
    ...
    return create_agent(...)

def criar_grafo():                         # é ESTA função que o langgraph.json chama
    return construir_agente(checkpointer=None)   # sem checkpointer: o Studio cuida do estado
```

Repare que o **mesmo** `construir_agente` é usado pelo terminal (`main()`) e pelo
Studio — não duplicamos a montagem. É a mesma separação de responsabilidades das
tools, aplicada ao agente.

**Como rodar o Studio (precisa do `.env` preenchido):**

```powershell
uv run langgraph dev
```

- Isso sobe um servidor local e abre o Studio no navegador. Você vê o grafo
  `agente` e pode mandar mensagens pela interface.
- Para **conferir** se o `langgraph.json` está correto sem subir o servidor:

```powershell
uv run langgraph validate
```

Deve responder `Configuration file ... is valid. (1 graph found)`.

> LangSmith x Studio: são complementares. O **Studio** é local e mostra o grafo
> e a execução; o **LangSmith** é na nuvem e guarda o histórico de traces. Com a
> chave do LangSmith configurada, o que você roda no Studio também aparece lá.

---

## Arquitetura de tools — a pasta `tools/`

Quando o projeto tem **muitas tools**, jogar todas no `agent.py` vira bagunça.
Por isso as tools moram num **pacote** separado, a pasta [`tools/`](tools):

```
tools/
├── __init__.py          # registro central: exporta TOOLS e o middleware de erro
├── _shared.py           # infra compartilhada: HTTP com timeout/erro + ToolExternaError
├── error_handling.py    # tratamento de erro central (wrap_tool_call middleware)
├── temperatura.py       # domínio: schema + service + @tool (cálculo puro)
└── cep.py               # domínio: schema + service + @tool (API ViaCEP)
```

### Anatomia de uma tool (3 camadas)

Cada tool é dividida em três partes, cada uma com **uma** responsabilidade:

1. **Schema** (Pydantic `BaseModel`): descreve e **valida** a entrada. O
   `description` de cada campo é lido pelo agente para saber o que preencher.
2. **Service**: a lógica pura (cálculo ou chamada de API), **sem LangChain** —
   testável sozinha e reutilizável.
3. **Tool** (`@tool`): a "casquinha" fina que liga schema + service e devolve
   **texto** para o agente.

> **Ligação do schema (pegadinha comum):** definir a classe Pydantic **não**
> conecta nada sozinho. Você liga passando `args_schema=` no decorator:
> `@tool("buscar_cep", args_schema=CEPInput)`. Sem isso, o schema fica decorativo.

### Registro central

O agente importa **só a vitrine** — uma linha:

```python
from tools import TOOLS, tratar_erros_de_tool
```

O [`tools/__init__.py`](tools/__init__.py) reúne todas as tools numa lista
`TOOLS`. O agente não sabe em qual arquivo cada tool mora (**baixo acoplamento**):
se você reorganizar os arquivos internos, o `agent.py` nem percebe.

### Como adicionar uma tool nova (o passo a passo)

1. Crie `tools/nova.py` com as 3 camadas (schema → service → `@tool`).
2. Importe e registre em `tools/__init__.py`:
   ```python
   from .nova import minha_tool
   TOOLS = [converter_temperatura, buscar_cep, minha_tool]  # <- adicione aqui
   ```
3. Pronto. O `agent.py` usa `*TOOLS`, então a tool entra **sozinha** no agente.
   Você **não mexe** no `agent.py`.

### Tratamento de erro central

Em vez de repetir `try/except` em cada tool, há **um** middleware
([`tools/error_handling.py`](tools/error_handling.py)) que envolve a execução de
**qualquer** tool. Se uma tool levanta `ToolExternaError`, ele devolve uma
mensagem amigável ao agente em vez de derrubar o programa. É a mesma lógica de
timeout/HTTP/JSON compartilhada em `tools/_shared.py` — escrita **uma vez**, usada
por todas as tools de API (princípio DRY: "não repita").

### Resiliência: fallback entre fontes

Quando uma tool depende de uma API que pode ficar instável ou limitar requisições
(HTTP 429), vale ter uma **segunda fonte** que cobre a primeira. O padrão é simples:
tente a fonte 1; se falhar, tente a fonte 2; só desista se **todas** falharem.

```python
def buscar_cnpj_service(cnpj):
    fontes = [
        f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}",   # 1ª tentativa
        f"https://minhareceita.org/{cnpj}",               # fallback
    ]
    ultimo_erro = None
    for url in fontes:                    # tenta cada fonte, em ordem
        try:
            return http_get_json(url)     # deu certo -> retorna e para
        except ToolAPIError as e:
            ultimo_erro = e               # falhou -> tenta a próxima
    raise ToolAPIError(f"Nenhuma fonte respondeu. Último erro: {ultimo_erro}")
```

Dica: escolha fontes que devolvam os **mesmos nomes de campo** — assim o código de
formatação não muda entre uma e outra. (Ex.: BrasilAPI e Minha Receita usam os
mesmos campos: `razao_social`, `municipio`, `uf`…) E **verifique o endpoint real
antes** de escrever a tool: a BrasilAPI, por exemplo, serve os dados sob `/api/`
(`https://brasilapi.com.br/api/cnpj/v1/...`) — sem o `/api/` você recebe a página
HTML do site, não o JSON.

### Quando isso vale a pena

- **1–2 tools simples:** um arquivo só resolve; essa estrutura é exagero.
- **A partir de ~3 tools, ou qualquer tool que chame API:** começa a compensar.
- **Muitas tools / vários domínios:** praticamente obrigatório.

---

## Consultar o banco em linguagem natural (SQL toolkit)

O agente também sabe **consultar o próprio PostgreSQL** a partir de perguntas em
português (ex.: "quantas conversas existem?"). Isso vem do **`SQLDatabaseToolkit`**
do `langchain-community`, que adiciona **4 ferramentas** de SQL às suas tools:

| Tool | O que faz |
|---|---|
| `sql_db_list_tables` | lista as tabelas do banco |
| `sql_db_schema` | mostra as colunas/tipos de uma tabela |
| `sql_db_query_checker` | pede ao modelo para **revisar** a query antes de rodar |
| `sql_db_query` | **executa** a query no banco |

O agente costuma usá-las **em sequência**: listar tabelas → ver o schema → revisar
→ rodar. Por isso o `system_prompt` orienta essa ordem — dar esse "roteiro" ajuda
o modelo a escolher a tool certa em cada etapa (sem isso, ele pode tentar rodar
uma query sem saber os nomes das tabelas).

### Onde fica no código

Tudo é montado dentro da fábrica `construir_agente` em [`agent.py`](agent.py), em
4 passos comentados: (1) `SQLDatabase.from_uri(...)`, (2) `SQLDatabaseToolkit(...)`,
(3) `get_tools()`, (4) juntar com `ferramentas = [*todas_as_tools, *sql_tools]`.

**Pegadinha de driver (importante):** o SQLAlchemy (usado por baixo) tenta o
`psycopg2` quando a URL começa com `postgresql://` — e nós usamos o **psycopg v3**.
Por isso o código troca o esquema para `postgresql+psycopg://` antes de conectar:

```python
sql_uri = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
```

> **Nota:** o `langchain-community` está em **descontinuação** ("sunset"). Ao rodar,
> você verá um `DeprecationWarning` — é esperado e não quebra nada. O toolkit ainda
> funciona; só saiba que, no longo prazo, pode migrar para um pacote dedicado.

### ⚠️ Segurança (leia com atenção)

O `SQLDatabaseToolkit` é **poderoso e perigoso** por padrão:

- A tool **`sql_db_query` executa QUALQUER SQL** que o modelo gerar — inclusive
  comandos que **MODIFICAM ou DESTROEM** dados: `DELETE`, `UPDATE`, `DROP`,
  `TRUNCATE`. Ela **não é** somente leitura.
- A `sql_db_query_checker` **só revisa a sintaxe** da query (se vai rodar sem erro).
  Ela **não** julga se a operação é segura — uma query `DROP TABLE` "bem escrita"
  passa na revisão.
- **O toolkit NÃO tem uma opção nativa confiável de "somente leitura".** Não existe
  um parâmetro que bloqueie `DELETE`/`DROP` de forma garantida. (Confirmei isso na
  versão instalada: os parâmetros do `SQLDatabase`, como `include_tables`, servem
  para limitar QUAIS tabelas o agente enxerga — não para impedir escrita.)

**O jeito certo de proteger (caminho para o futuro — não precisa fazer agora):**
crie um usuário PostgreSQL **somente leitura** e use a connection string DELE para
o toolkit. A segurança fica no **banco**, não no código — é à prova de "jailbreak"
do modelo. O SQL seria:

```sql
-- 1. cria um usuário só de leitura
CREATE USER agente_readonly WITH PASSWORD 'uma-senha-forte';
-- 2. deixa ele CONECTAR e VER o schema
GRANT CONNECT ON DATABASE agente_ia TO agente_readonly;
GRANT USAGE ON SCHEMA public TO agente_readonly;
-- 3. concede APENAS SELECT (leitura) nas tabelas atuais e futuras
GRANT SELECT ON ALL TABLES IN SCHEMA public TO agente_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO agente_readonly;
```

Depois, você teria no `.env` uma segunda URL, por exemplo
`DATABASE_URL_RO=postgresql://agente_readonly:...@localhost:5432/agente_ia`, e
passaria essa URL ao `SQLDatabase` (mantendo a `DATABASE_URL` normal para o
checkpointer e as suas tabelas). Assim, mesmo que o modelo tente um `DELETE`, o
banco **recusa** — o usuário não tem permissão. Enquanto não fizer isso, use o SQL
toolkit só em um banco de estudo, ciente do risco.

---

## Segurança (obrigatório)

- **Todos os segredos vêm do `.env`** — chaves de API e a URL do banco. No
  código, usamos `load_dotenv()` + `os.environ[...]`. **Nunca** escrevemos uma
  chave ou senha direto no `.py`.
- **`.gitignore`** ([arquivo](.gitignore)) ignora `.env`, `.venv/` e
  `__pycache__/`. Isso impede que suas chaves vazem no GitHub. É **obrigatório**.
- **`.env.example`** ([arquivo](.env.example)) é o **modelo sem valores reais**:
  mostra quais variáveis existem, sem expor segredos. Esse pode ir para o GitHub.
- **Queries parametrizadas (`%s`)** protegem contra **SQL injection** (seção 3.4).

---

## Preparado para o futuro

**Adicionar novas tools** — em [`agent.py`](agent.py), a lista `tools` é o único
lugar que você mexe. Crie/importe a nova tool e inclua na lista:

```python
tools = [busca_web]            # <- inclua novas ferramentas aqui: [busca_web, nova_tool, ...]
```

O agente passa a considerar a nova ferramenta automaticamente (ele lê a
descrição dela e decide quando usar).

**Trocar o modelo (OpenAI → Gemini)** — troque só a string do modelo:

```python
modelo = "openai:gpt-3.5-turbo"           # atual
# modelo = "google_genai:gemini-1.5-flash"  # futuro (precisa da GOOGLE_API_KEY no .env)
```

**Receber mensagens via webhook** — hoje conversamos pelo terminal. Um **webhook**
é um endereço (endpoint) que recebe uma mensagem por HTTP e devolve a resposta.
Além de abrir o agente para o mundo (site, WhatsApp), ele resolve um problema que
o terminal **não** resolve: a **identidade** do usuário.

### Identidade: por que o terminal não basta

- **Identificação** = perguntar quem é você. **Autenticação** = provar quem é.
- No terminal, se você `input()` o login (ou até um telefone), **não prova nada** —
  qualquer um pode digitar o dado de outra pessoa. Não serve como identidade.
- No **webhook**, o identificador (ex.: número de telefone) **chega na requisição,
  vindo da plataforma** (WhatsApp/Telegram), que já validou aquele número. O
  usuário não digita — logo, não forja. Por isso o `thread_id` costuma **ser** o
  número: um identificador validado pela origem.
- ⚠️ **Mas o webhook em si também precisa ser verificado:** a plataforma **assina**
  a requisição com um segredo; seu código confere essa assinatura **antes** de
  confiar no remetente. Sem isso, um impostor pode forjar a requisição. (Essa
  validação depende de infraestrutura externa — conta na Meta/Twilio, URL pública.)

### O endpoint (FastAPI)

Instale as dependências e monte o agente **uma vez** (na subida do servidor); o
endpoint só faz `invoke`. Arquivo `webhook.py`:

```python
from fastapi import FastAPI
from pydantic import BaseModel
# ... (montagem única do agente + checkpointer, igual ao agent.py) ...

app = FastAPI()

class Mensagem(BaseModel):     # o FastAPI valida sozinho (falta de campo = erro 422)
    de: str                    # identificador do remetente — VEM DO CANAL, não digitado
    texto: str

@app.post("/webhook")
def receber(msg: Mensagem):
    # PRODUÇÃO: verifique aqui a ASSINATURA da requisição antes de confiar no "de".
    thread_id = msg.de.strip()                      # a identidade veio de fora
    config = {"configurable": {"thread_id": thread_id}}
    resultado = agente.invoke(
        {"messages": [{"role": "user", "content": msg.texto}]}, config,
    )
    return {"resposta": resultado["messages"][-1].content}
```

Dependências e execução:

```powershell
uv add fastapi uvicorn
uv run uvicorn webhook:app --reload
```

Teste sem ferramenta extra: o FastAPI cria uma página de testes automática em
`http://127.0.0.1:8000/docs` (POST /webhook → Try it out). Mesmo `de` = mesma
memória; `de` diferente = conversa isolada — é a base do multi-usuário.

> Cada projeto tem sua **própria `.venv`**: instalar o FastAPI num projeto não o
> instala em outro. Se der `ModuleNotFoundError: fastapi`, rode `uv add fastapi
> uvicorn` **na pasta daquele projeto**.

---

## Versionamento com Git (por último)

Agora que tudo está criado, vamos enviar ao seu repositório. **Antes do primeiro
commit, confirme que o `.gitignore` está funcionando** — o `.env` NÃO pode ser
enviado.

### Passo 0 — Iniciar o Git e conferir o `.gitignore` ANTES de tudo

```powershell
git init
```

- `git init` cria o repositório Git nesta pasta (uma pasta oculta `.git`).

Agora **o teste de segurança** — veja o que o Git pretende enviar:

```powershell
git status
```

- **Procure na lista: o `.env` NÃO pode aparecer.** Devem aparecer `README.md`,
  `agent.py`, `pyproject.toml`, `.env.example`, `.gitignore`, a pasta `sql/`...
  mas **nunca** o `.env` nem a `.venv/`.
- Confirmação extra, específica para o `.env`:

```powershell
git check-ignore .env
```

- Se ele **imprimir `.env`**, quer dizer que o arquivo **está sendo ignorado**
  (perfeito, é o que queremos). Se **não imprimir nada**, o `.gitignore` não está
  pegando — **PARE** e verifique o arquivo `.gitignore` antes de continuar.

### Passo 1 — Os comandos, na ordem certa

Depois de confirmar que o `.env` está ignorado, rode na ordem:

```bash
echo "# LangChain1.0" >> README.md
```

```bash
git add README.md
```

```bash
git commit -m "first commit"
```

```bash
git branch -M main
```

```bash
git remote add origin https://github.com/renanbforte/LangChain1.0.git
```

```bash
git push -u origin main
```

O que cada um faz:
- `echo "# LangChain1.0" >> README.md` — acrescenta um título ao README (o `>>`
  adiciona no final, sem apagar o conteúdo existente).
- `git add README.md` — coloca o README na "área de preparação" (staging).
- `git commit -m "first commit"` — grava o primeiro ponto na história do projeto,
  com a mensagem "first commit".
- `git branch -M main` — renomeia a branch atual para `main` (padrão do GitHub).
- `git remote add origin <url>` — liga o seu repositório local ao repositório
  remoto no GitHub (apelidado `origin`).
- `git push -u origin main` — **envia** os commits para o GitHub. O `-u` memoriza
  o destino, para que nas próximas vezes você use só `git push`.

> **Quer enviar TODOS os arquivos** (não só o README) neste primeiro envio?
> Depois do `git init` e do teste do `.gitignore`, use `git add .` no lugar de
> `git add README.md` — o `.` adiciona tudo que **não** está no `.gitignore`
> (ou seja, tudo menos `.env`, `.venv/` e `__pycache__/`). Depois siga com
> `git commit`, `git branch -M main`, `git remote add origin ...` e `git push`.

---

## Problemas comuns no Windows

Erros reais que aparecem no dia a dia (Windows + PowerShell + uv) e como resolver.

### 1. `uv sync` falha com "operação de nuvem / os error 396"

**Sintoma:** ao rodar `uv sync`, aparece algo como *"Failed to hardlink... A
operação de nuvem não pode ser executada em um arquivo com links físicos
incompatíveis. (os error 396)"* e a `.venv` fica incompleta.

**Causa:** a pasta do projeto é gerenciada por uma **sincronização em nuvem** —
OneDrive, **Google Drive** ou **Dropbox** para desktop. O `uv` usa *hardlinks* por
padrão; esses sincronizadores não suportam. (Como confirmar: o erro `396` é da
categoria "arquivos em nuvem" do Windows — se aparece, algum sincronizador está
tocando a pasta, mesmo que o caminho pareça local.)

**Correção:** apague a `.venv` quebrada e refaça em modo cópia:

```powershell
Remove-Item -Recurse -Force .venv
uv sync --link-mode=copy
```

Para valer sempre: `setx UV_LINK_MODE copy` (e reabra o terminal). **Melhor:**
mantenha o projeto **fora** de qualquer pasta sincronizada — o mais seguro é a
raiz do disco, tipo `C:\Projetos\...` (fora de `C:\Users\...`).

### 2. `ModuleNotFoundError` (ex.: "No module named 'jsonpatch'") ao importar

**Causa mais comum:** a `.venv` está **corrompida ou foi copiada** de outra pasta.
Venv **não é portátil** — ela guarda caminhos absolutos e não funciona se copiada.
(Muitas vezes é o mesmo problema do OneDrive acima, que interrompeu a instalação.)

**Correção:** recrie a `.venv` do zero (nunca copie a `.venv` entre pastas):

```powershell
Remove-Item -Recurse -Force .venv
uv sync --link-mode=copy
```

### 3. "program not found" ou nada acontece ao rodar

- `run agent.py` → **errado**: `run` sozinho não existe. Use `uv run`.
- `uv run agent.py` → confira o **nome exato** do arquivo (é `agent.py`? `agente.py`?).
- Forma correta: `uv run python agent.py`.
- Se rodar e **não aparecer nada**, o arquivo pode estar **vazio** (0 bytes) —
  rodar arquivo vazio não dá erro, só sai calado.

### 4. Emojis/acentos quebrados no terminal (`UnicodeEncodeError`)

O console do Windows usa cp1252. Alguns comandos (ex.: `langgraph --help`) imprimem
emoji e falham. Prefixe com `PYTHONIOENCODING=utf-8` (no PowerShell:
`$env:PYTHONIOENCODING="utf-8"` antes do comando). Não afeta o agente em si.

---

## Problemas comuns ao construir o agente

Tropeços que aparecem enquanto você monta o agente passo a passo (todos reais).

### 5. Rodei o arquivo e não apareceu NADA (sem erro)

O arquivo `.py` provavelmente está **vazio** (0 bytes). Rodar um arquivo vazio não
dá erro — o Python abre, não acha nada e sai calado. Confirme que o código está
salvo. E lembre do comando certo: `uv run python agente.py` (não `run agente.py`).

### 6. `openai.BadRequestError` sobre `tool_calls` sem resposta

Mensagem: *"An assistant message with 'tool_calls' must be followed by tool
messages..."*. **Causa:** o histórico salvo daquela conversa (thread) ficou
**inconsistente** — o agente pediu uma tool, mas a resposta da tool não foi salva.
Acontece quando uma execução é **interrompida no meio de uma chamada de tool**
(ex.: `Ctrl+C`) ou quando uma tool **crasha sem tratamento de erro**.

**Correção rápida:** comece uma conversa nova, trocando o `thread_id` (ex.:
`"conversa-1"` → `"conversa-2"`). **Correção definitiva:** use o middleware de
tratamento de erro (`wrap_tool_call`) — com ele, uma falha de tool vira uma
mensagem limpa e o histórico nunca fica "pendurado". E, para sair, digite `sair`
em vez de `Ctrl+C`.

### 7. Uma tool derruba o programa inteiro

Se uma tool levanta uma exceção (rede, 429, dado inválido) **sem** o middleware de
erro, o `agente.invoke(...)` propaga o erro e o programa cai. Adicione o
`wrap_tool_call` em `create_agent(middleware=[...])`: a falha vira uma `ToolMessage`
amigável, o agente responde com jeito e o programa continua vivo. Veja
[Tratamento de erro central](#tratamento-de-erro-central).

### 8. A API respondeu HTML em vez de JSON / erro de status

Antes de escrever uma tool, **teste a URL da API de verdade** (com `requests` num
script curto). Se vier HTML, o endereço provavelmente está incompleto (ex.: a
BrasilAPI precisa de `/api/` no caminho). Se vier **HTTP 429**, é limite de
requisições — espere um pouco ou use [fallback entre fontes](#resiliência-fallback-entre-fontes).

---

## Resumo dos arquivos do projeto

| Arquivo | Para que serve |
|---|---|
| [`README.md`](README.md) | Este guia. |
| [`agent.py`](agent.py) | O agente completo, comentado linha a linha. |
| [`pyproject.toml`](pyproject.toml) | Lista de dependências (lida pelo `uv`). |
| [`.env.example`](.env.example) | Modelo de segredos (sem valores reais). |
| [`.gitignore`](.gitignore) | Impede o envio de `.env`, `.venv/`, `__pycache__/`. |
| [`sql/criar_tabelas.sql`](sql/criar_tabelas.sql) | Cria `conversas` e `mensagens`. |
| [`sql/consultar_conversas.sql`](sql/consultar_conversas.sql) | Consulta com JOIN para ler o histórico. |

**Ordem sugerida para rodar tudo:**
1. Parte 1 (instalar PostgreSQL + criar banco `agente_ia`).
2. `uv sync` e preencher o `.env`.
3. `psql -U postgres -d agente_ia -f sql\criar_tabelas.sql` (cria as tabelas).
4. `uv run python agent.py` (conversar com o agente).
5. pgAdmin → banco `agente_ia` → Query Tool → rodar o JOIN (ver as conversas).
6. Git (enviar ao GitHub, conferindo o `.gitignore` antes).
