# =============================================================================
# tools/temperatura.py  —  Tool de conversão de temperatura (cálculo puro)
# -----------------------------------------------------------------------------
# Esta tool NÃO chama API nenhuma; é só matemática. Serve para mostrar a
# "anatomia" de uma tool bem feita e a SEPARAÇÃO DE RESPONSABILIDADES:
#
#   1) SCHEMA   (TemperaturaInput) -> descreve e VALIDA a entrada.
#   2) SERVICE  (converter_..._service) -> a lógica pura, testável sem LangChain.
#   3) TOOL     (@tool)            -> a "casquinha" fina que liga schema + service
#                                     e devolve texto para o agente.
#
# Por que separar service da tool? Porque assim a lógica de negócio vive sozinha:
# você consegue testá-la, reusá-la em outro lugar (uma API web, um script) e
# trocá-la sem mexer no LangChain. A tool vira só um ADAPTADOR.
# =============================================================================

from pydantic import BaseModel, Field, field_validator   # validação de entrada
from langchain_core.tools import tool                     # o decorator @tool


# -----------------------------------------------------------------------------
# 1) SCHEMA — o "contrato" da entrada, com validação automática (Pydantic)
# -----------------------------------------------------------------------------
# Cada campo vira um argumento da tool. O `description` de cada Field é LIDO
# PELO AGENTE: é assim que o modelo entende o que preencher em cada campo.
class TemperaturaInput(BaseModel):
    """Entrada da conversão de temperatura."""

    # `float` = número com casas decimais. Field(...) com "..." = obrigatório.
    valor: float = Field(..., description="O número da temperatura a converter, ex.: 100")

    # As unidades são texto. Aceitamos C, F ou K (Celsius, Fahrenheit, Kelvin).
    de: str = Field(..., description="Unidade de ORIGEM: 'C', 'F' ou 'K'")
    para: str = Field(..., description="Unidade de DESTINO: 'C', 'F' ou 'K'")

    # Um validador: roda ANTES de a tool executar. Se algo estiver errado aqui,
    # a tool nem chega a rodar — o Pydantic barra a entrada inválida.
    # @field_validator("de", "para") = aplica esta função aos dois campos.
    @field_validator("de", "para")
    @classmethod
    def normalizar_unidade(cls, v):
        # v é o valor que o usuário/agente mandou (ex.: "c" ou " f ").
        unidade = v.strip().upper()           # tira espaços e deixa MAIÚSCULO
        if unidade not in {"C", "F", "K"}:     # só aceitamos essas três
            # Levantar ValueError aqui faz o Pydantic recusar a entrada com
            # uma mensagem explicando o motivo.
            raise ValueError("Unidade deve ser 'C', 'F' ou 'K'.")
        return unidade                         # devolvemos já normalizado


# -----------------------------------------------------------------------------
# 2) SERVICE — a lógica pura da conversão (sem LangChain, 100% testável)
# -----------------------------------------------------------------------------
# Estratégia clássica: converta tudo para uma unidade "pivô" (Celsius) e depois
# de Celsius para o destino. Assim você não precisa de uma fórmula para cada par.

def _para_celsius(valor, unidade):
    """Converte qualquer unidade suportada PARA Celsius."""
    if unidade == "C":
        return valor                       # já está em Celsius
    if unidade == "F":
        return (valor - 32) * 5 / 9        # Fahrenheit -> Celsius
    # Só sobra K:
    return valor - 273.15                  # Kelvin -> Celsius


def _de_celsius(celsius, unidade):
    """Converte de Celsius PARA a unidade desejada."""
    if unidade == "C":
        return celsius                     # destino é Celsius
    if unidade == "F":
        return celsius * 9 / 5 + 32        # Celsius -> Fahrenheit
    return celsius + 273.15                # Celsius -> Kelvin


def converter_temperatura_service(valor, de, para):
    """Recebe valor + unidades e devolve o número convertido (float)."""
    celsius = _para_celsius(valor, de)     # passo 1: origem -> Celsius
    return _de_celsius(celsius, para)      # passo 2: Celsius -> destino


# -----------------------------------------------------------------------------
# 3) TOOL — a casquinha fina que o agente enxerga
# -----------------------------------------------------------------------------
# @tool("nome", args_schema=...) transforma a função numa ferramenta do agente.
#   - "converter_temperatura" é o NOME que o agente usa para chamá-la.
#   - args_schema=TemperaturaInput LIGA o schema Pydantic à tool. (Sem isto, o
#     Pydantic ficaria definido mas NÃO seria usado — que é o bug clássico.)
# A DOCSTRING abaixo é CRÍTICA: ela é a "propaganda" da tool. O agente lê esta
# descrição para decidir QUANDO usar esta ferramenta em vez de outra. Docstring
# vaga = agente escolhe errado. Seja específico sobre o que ela faz e quando usar.
@tool("converter_temperatura", args_schema=TemperaturaInput)
def converter_temperatura(valor, de, para):
    """Converte uma temperatura entre Celsius (C), Fahrenheit (F) e Kelvin (K).

    Use quando o usuário pedir para converter temperaturas, por exemplo:
    'quantos graus Fahrenheit são 100 Celsius?' ou 'converta 300 K para C'.
    """
    resultado = converter_temperatura_service(valor, de, para)  # chama o service
    # round(x, 2) arredonda para 2 casas. A tool devolve TEXTO (o agente lê texto).
    return f"{valor} {de} equivalem a {round(resultado, 2)} {para}."
