-- ============================================================================
-- criar_tabelas.sql
-- ----------------------------------------------------------------------------
-- Cria DUAS tabelas para guardar o histórico de conversas em TEXTO LIMPO
-- (legível por humanos), separadas das tabelas internas do LangGraph.
--
-- Relação: UM-PARA-MUITOS
--   - 1 linha em "conversas"  ->  MUITAS linhas em "mensagens".
--   - Ou seja: uma conversa tem várias mensagens (pergunta, resposta, ...).
--
-- Rode este arquivo UMA VEZ, conectado ao banco "agente_ia".
-- No psql:   \i 'caminho/para/criar_tabelas.sql'
-- Ou cole o conteúdo no Query Tool do pgAdmin (ver README, Parte 3).
-- ============================================================================


-- ----------------------------------------------------------------------------
-- TABELA 1: conversas
-- Cada linha aqui representa UMA conversa inteira (uma sessão de bate-papo).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversas (
    -- id: número que identifica a conversa de forma única.
    --   SERIAL       = número inteiro que o banco preenche sozinho e AUTOINCREMENTA
    --                  (1, 2, 3, ...). Você nunca precisa informar esse valor.
    --   PRIMARY KEY  = "chave primária". É o identificador oficial da linha.
    --                  Não pode se repetir e não pode ser vazio (NULL).
    id SERIAL PRIMARY KEY,

    -- thread_id: o "código da conversa" que o LangGraph usa para separar sessões.
    --   TEXT    = texto de tamanho livre.
    --   UNIQUE  = não pode haver duas conversas com o MESMO thread_id.
    --             Isso garante que cada sessão tenha UMA única linha aqui.
    --             (É essa restrição que faz o "ON CONFLICT" funcionar no Python.)
    --   NOT NULL = este campo é obrigatório; não pode ficar vazio.
    thread_id TEXT UNIQUE NOT NULL,

    -- titulo: um nome amigável opcional para a conversa (pode ficar vazio).
    titulo TEXT,

    -- criada_em: data e hora em que a conversa foi criada.
    --   TIMESTAMP    = tipo que guarda data + hora.
    --   DEFAULT NOW() = se você não informar um valor, o banco usa a hora ATUAL
    --                   automaticamente no momento da inserção.
    criada_em TIMESTAMP DEFAULT NOW()
);


-- ----------------------------------------------------------------------------
-- TABELA 2: mensagens
-- Cada linha aqui é UMA mensagem individual dentro de uma conversa.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mensagens (
    -- id da mensagem (autoincrementado, chave primária), igual ao explicado acima.
    id SERIAL PRIMARY KEY,

    -- conversa_id: liga esta mensagem à conversa dona dela.
    --   INTEGER              = número inteiro (vai guardar o "id" de conversas).
    --   REFERENCES conversas(id) = CHAVE ESTRANGEIRA ("foreign key").
    --       Significa: o valor aqui TEM que existir na coluna "id" da tabela
    --       "conversas". Você não consegue salvar uma mensagem apontando para
    --       uma conversa que não existe. É isso que garante a integridade dos
    --       dados e cria a relação um-para-muitos.
    --   NOT NULL             = toda mensagem OBRIGATORIAMENTE pertence a uma conversa.
    conversa_id INTEGER NOT NULL REFERENCES conversas(id),

    -- papel: quem "falou" a mensagem. Usamos dois valores:
    --   'user'      -> a pergunta digitada por você.
    --   'assistant' -> a resposta gerada pelo agente de IA.
    papel TEXT NOT NULL,

    -- conteudo: o texto da mensagem em si (a pergunta ou a resposta).
    conteudo TEXT NOT NULL,

    -- criada_em: quando esta mensagem foi salva (preenchido automaticamente).
    --   É esta coluna que usamos para ORDENAR as mensagens na ordem cronológica.
    criada_em TIMESTAMP DEFAULT NOW()
);
