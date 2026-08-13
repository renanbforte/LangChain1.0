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

**Receber mensagens via webhook** — hoje conversamos pelo terminal. No futuro,
um sistema externo (site, WhatsApp) pode mandar uma mensagem por HTTP e receber
a resposta. Isso se chama **webhook**: um endereço (endpoint) que espera
requisições. O **esqueleto comentado** (com FastAPI) já está no final do
[`agent.py`](agent.py), pronto para você preencher — **nada disso roda ainda**,
é só o plano deixado no lugar certo.

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
