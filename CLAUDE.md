# CLAUDE.md

Contexto para assistentes de IA (Claude Code) que trabalham neste repositório.
Projeto de **estudo** de um agente de IA com LangChain 1.0 + LangGraph. O dono
está **aprendendo do zero** — priorize clareza e explicação sobre esperteza.
O `README.md` é o guia completo e a fonte de verdade didática.

## Ambiente

- **SO:** Windows. **Terminal:** PowerShell. **Gerenciador:** `uv`. **Editor:** VS Code.
- **Console Windows é cp1252:** imprimir emoji/acentos pode dar `UnicodeEncodeError`.
  Ao rodar comandos que emitem emoji (ex.: `langgraph --help`), prefixe com
  `PYTHONIOENCODING=utf-8`.
- **Modelo padrão:** OpenAI `gpt-3.5-turbo` (trocável para Gemini mudando a string
  do modelo em `agent.py`, função `construir_agente`).

## Comandos

```bash
uv sync                                   # instala dependências (cria .venv)
uv run python agent.py                    # roda o agente no terminal (loop de conversa)
uv run langgraph validate                 # valida o langgraph.json
uv run langgraph dev                      # abre o LangGraph Studio (grafo visual) local
psql -U postgres -d agente_ia -f sql\criar_tabelas.sql   # cria tabelas de histórico
```

Pré-requisitos para RODAR (não só editar): PostgreSQL rodando + banco `agente_ia`
criado + `.env` preenchido. Sem isso, dá para editar/entender o código, mas não
executar de ponta a ponta.

## Arquitetura (visão rápida)

- **`agent.py`** — ponto central. Blocos comentados. Lê segredos do `.env`,
  monta o agente e roda o loop de terminal.
  - `construir_agente(checkpointer=None)` — **fábrica** do agente (tools +
    middlewares). Reusada pelo `main()` e pelo Studio. NÃO duplicar a montagem.
  - `criar_grafo()` — alvo do `langgraph.json` (chama a fábrica sem checkpointer).
  - `main()` — abre o `PostgresSaver` num `with`, monta o agente e roda o loop.
- **`tools/`** — pacote de tools. Padrão de cada tool: **schema (Pydantic) →
  service (lógica pura) → `@tool` (casquinha)**. `tools/__init__.py` exporta a
  lista `TOOLS` (registro central) e o middleware `tratar_erros_de_tool`.
  Infra HTTP compartilhada em `tools/_shared.py`.
- **`sql/`** — `criar_tabelas.sql` (tabelas `conversas`/`mensagens`, texto limpo)
  e `consultar_conversas.sql` (JOIN para ler o histórico).
- **Memória:** o LangGraph salva no PostgreSQL via `PostgresSaver` (checkpointer);
  em paralelo, as tabelas `conversas`/`mensagens` guardam o histórico legível.
- **`langgraph.json`** — config do LangGraph Studio; aponta para `agent.py:criar_grafo`.

## Convenções (seguir)

- **Segredos SÓ do `.env`** (`load_dotenv()` + `os.environ`/`os.getenv`). NUNCA
  hardcodar chave/senha. `.env` é ignorado pelo Git — jamais commitar.
- **SQL sempre parametrizado com `%s`** (nunca f-string em query) — anti SQL injection.
- **Nova tool:** criar arquivo em `tools/`, registrar em `tools/__init__.py`.
  NÃO editar `agent.py` para isso (ele usa `*TOOLS`).
- **Ligar schema à tool:** `@tool("nome", args_schema=MeuSchema)`.
- **Comentar bastante**, em português, no nível de quem está aprendendo.

## APIs verificadas nesta versão (LangChain 1.x) — não assumir versões antigas

- `create_agent` vem de `langchain.agents`.
- `SummarizationMiddleware` (de `langchain.agents.middleware`) usa **um** parâmetro
  `trigger=(tipo, limite)`: `("tokens", N)` ou `("messages", N)`. NÃO existe
  `max_tokens_before_summary` (API antiga).
- `wrap_tool_call` (de `langchain.agents.middleware`) é um **middleware**: decora
  uma função `(request, handler)` e vai em `create_agent(middleware=[...])`.
- Tools/middlewares entram no agente por `create_agent(tools=..., middleware=[...])`.
- Se em dúvida sobre uma API, **inspecione a biblioteca instalada** (`inspect.signature`)
  em vez de assumir — a stack muda rápido.

## Não fazer

- Não commitar `.env` (nem qualquer segredo). Conferir com `git check-ignore .env`
  antes do primeiro commit de uma sessão.
- Não trocar/remover `PostgresSaver`, as tools existentes ou o loop sem pedido claro.
- Não publicar/commitar/push sem confirmação do dono.
