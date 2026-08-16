# =============================================================================
# tools/_shared.py  —  Infraestrutura COMPARTILHADA entre tools
# -----------------------------------------------------------------------------
# Por que este arquivo existe?
#   Várias tools vão chamar APIs externas (ViaCEP hoje; amanhã, cotação, clima...).
#   TODAS precisam da MESMA lógica chata: colocar timeout, checar o status HTTP,
#   ler o JSON com segurança e traduzir falhas em uma mensagem clara.
#   Em vez de copiar esse código em cada tool (repetição = bug em vários lugares),
#   centralizamos aqui. Isso se chama DRY ("Don't Repeat Yourself" - não repita).
#
# O "_" no começo do nome (_shared) é uma convenção do Python que sinaliza
# "isto é interno do pacote; quem usa o projeto de fora não precisa importar".
# =============================================================================

import requests   # biblioteca HTTP; declarada como dependência no pyproject.toml


# -----------------------------------------------------------------------------
# UMA exceção própria para falhas de tools externas.
# -----------------------------------------------------------------------------
# Criar a nossa própria classe de erro (herdando de Exception) nos deixa
# DISTINGUIR "um erro esperado da minha tool" de "um bug qualquer do Python".
# Mais adiante, o middleware de tratamento de erro captura EXATAMENTE este tipo
# e devolve uma mensagem amigável ao agente, sem derrubar o programa.
class ToolExternaError(Exception):
    """Erro esperado ao chamar um serviço externo (rede, status HTTP, JSON)."""
    # `pass` = corpo vazio; a classe não precisa de nada além do nome e da
    # docstring. Toda a utilidade vem de ela ser um TIPO que podemos capturar.
    pass


# -----------------------------------------------------------------------------
# Função utilitária: GET em uma URL e devolve o JSON, com boas práticas.
# -----------------------------------------------------------------------------
def http_get_json(url, *, timeout=8):
    """Faz um GET na `url` e devolve o corpo como dicionário (JSON).

    Boas práticas embutidas:
      - timeout: nunca esperar para sempre (evita o programa "travar").
      - checagem de status HTTP: 200 = ok; qualquer outro = erro claro.
      - leitura segura do JSON: se não vier JSON válido, erro claro.

    Em qualquer falha, levanta ToolExternaError com uma mensagem legível.
    """
    # O `*` na assinatura força `timeout` a ser passado pelo NOME (timeout=5),
    # nunca por posição. Isso deixa as chamadas mais legíveis e à prova de engano.

    try:
        # timeout=timeout: se o servidor não responder em X segundos, aborta.
        # Sempre defina timeout em chamadas de rede — é a boa prática nº 1.
        resposta = requests.get(url, timeout=timeout)
    except requests.Timeout:
        # A conexão demorou mais que o timeout. Traduzimos para o nosso erro.
        raise ToolExternaError(f"O serviço demorou demais para responder ({url}).")
    except requests.RequestException as e:
        # RequestException é a "mãe" de todos os erros do requests (sem internet,
        # DNS falhou, conexão recusada...). Capturamos tudo isso de uma vez.
        raise ToolExternaError(f"Falha de rede ao acessar o serviço: {e}")

    # Chegou uma resposta. Mas "chegou resposta" não é o mesmo que "deu certo":
    # o servidor pode ter respondido 404 (não encontrado) ou 500 (erro dele).
    if resposta.status_code != 200:
        raise ToolExternaError(
            f"O serviço respondeu com status HTTP {resposta.status_code}."
        )

    try:
        # .json() converte o texto da resposta em dicionário Python.
        # Se o corpo não for JSON válido, o requests levanta ValueError.
        return resposta.json()
    except ValueError:
        raise ToolExternaError("A resposta do serviço não veio em JSON válido.")
