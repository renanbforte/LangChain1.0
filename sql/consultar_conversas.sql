-- ============================================================================
-- consultar_conversas.sql
-- ----------------------------------------------------------------------------
-- Mostra o histórico completo de conversas em TEXTO LIMPO, juntando as duas
-- tabelas (conversas + mensagens) com um JOIN e ordenando por data.
--
-- Rode no Query Tool do pgAdmin (ver README, Parte 3) ou no psql.
-- ============================================================================

SELECT
    -- Colunas que queremos ver no resultado. O apelido antes do ponto
    -- (c. ou m.) diz de QUAL tabela cada coluna vem.
    c.thread_id     AS conversa,   -- o código da conversa (vem da tabela conversas)
    m.papel         AS quem_falou, -- 'user' ou 'assistant' (vem da tabela mensagens)
    m.conteudo      AS mensagem,   -- o texto da mensagem
    m.criada_em     AS quando      -- data/hora em que foi salva
FROM
    -- Tabela principal da consulta: mensagens. Damos a ela o apelido "m"
    -- para não precisar escrever "mensagens." toda hora.
    mensagens AS m
JOIN
    -- JOIN = "juntar". Para cada mensagem, buscamos a conversa dona dela.
    -- Damos o apelido "c" para a tabela conversas.
    conversas AS c
    -- ON = a REGRA que liga as duas tabelas: pegue a linha de "conversas"
    -- cujo "id" seja igual ao "conversa_id" guardado na mensagem.
    -- É exatamente a chave estrangeira funcionando na prática.
    ON m.conversa_id = c.id
ORDER BY
    -- Ordena o resultado do mais ANTIGO para o mais NOVO, para você ler a
    -- conversa de cima para baixo, na ordem em que aconteceu.
    m.criada_em ASC;


-- ----------------------------------------------------------------------------
-- VARIAÇÃO ÚTIL: ver apenas UMA conversa específica.
-- Descomente e troque 'conversa-1' pelo thread_id que você quer inspecionar.
-- ----------------------------------------------------------------------------
-- SELECT c.thread_id, m.papel, m.conteudo, m.criada_em
-- FROM mensagens AS m
-- JOIN conversas AS c ON m.conversa_id = c.id
-- WHERE c.thread_id = 'conversa-1'   -- filtra só essa conversa
-- ORDER BY m.criada_em ASC;
