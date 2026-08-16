# =============================================================================
# tools/cep.py  —  Tool de busca de endereço por CEP (API ViaCEP)
# -----------------------------------------------------------------------------
# Mesma anatomia da tool de temperatura (schema -> service -> tool), mas agora
# a lógica CHAMA UMA API EXTERNA. Repare que ela NÃO repete a lógica de
# timeout/erro/JSON: isso vem pronto de tools/_shared.py. É a separação de
# responsabilidades pagando dividendos — a tool de CEP só cuida de CEP.
# =============================================================================

from pydantic import BaseModel, Field, field_validator   # validação de entrada
from langchain_core.tools import tool                     # o decorator @tool

# Importações RELATIVAS (o ponto ".") = "do mesmo pacote tools/".
# Trazemos o utilitário HTTP e o tipo de erro compartilhados.
from ._shared import http_get_json, ToolExternaError


# -----------------------------------------------------------------------------
# 1) SCHEMA — valida o CEP ANTES de gastar uma chamada de rede
# -----------------------------------------------------------------------------
class CEPInput(BaseModel):
    """Entrada da busca de CEP."""

    cep: str = Field(..., description="CEP brasileiro com 8 dígitos, ex.: 01001000")

    @field_validator("cep")
    @classmethod
    def validar_cep(cls, v):
        # Removemos qualquer coisa que não seja dígito (aceita "01001-000",
        # "01001 000" etc.). O "".join(...) monta de volta só os números.
        somente_digitos = "".join(c for c in v if c.isdigit())
        if len(somente_digitos) != 8:                 # CEP válido tem 8 dígitos
            raise ValueError("O CEP deve conter exatamente 8 dígitos.")
        return somente_digitos                        # devolve limpo, pronto para a URL


# -----------------------------------------------------------------------------
# 2) SERVICE — a chamada real à API ViaCEP (sem LangChain)
# -----------------------------------------------------------------------------
def buscar_cep_service(cep):
    """Consulta o ViaCEP e devolve um dicionário com os dados do endereço.

    Levanta ToolExternaError se o CEP não existir ou se a API falhar.
    """
    # Montamos a URL do ViaCEP. O CEP já vem validado (8 dígitos) do schema.
    url = f"https://viacep.com.br/ws/{cep}/json/"

    # http_get_json já aplica timeout, checa status e lê o JSON com segurança.
    dados = http_get_json(url, timeout=8)

    # PEGADINHA IMPORTANTE: o ViaCEP responde HTTP 200 MESMO quando o CEP não
    # existe — mas o corpo vem como {"erro": true}. Ou seja, status 200 não
    # garante sucesso "de negócio". Por isso checamos esse campo aqui.
    if dados.get("erro"):
        raise ToolExternaError(f"CEP {cep} não encontrado.")

    return dados   # dicionário com logradouro, bairro, localidade, uf, etc.


# -----------------------------------------------------------------------------
# 3) TOOL — a casquinha que o agente enxerga
# -----------------------------------------------------------------------------
@tool("buscar_cep", args_schema=CEPInput)
def buscar_cep(cep):
    """Busca o endereço (rua, bairro, cidade, estado) de um CEP brasileiro.

    Use quando o usuário informar um CEP e quiser saber o endereço, por
    exemplo: 'que endereço é o CEP 01001-000?'.
    """
    dados = buscar_cep_service(cep)   # chama o service (pode levantar ToolExternaError)
    # Montamos uma frase legível com os campos que interessam.
    # .get("campo", "") evita erro se algum campo vier ausente.
    return (
        f"CEP {dados.get('cep', cep)}: "
        f"{dados.get('logradouro', '')}, "
        f"{dados.get('bairro', '')}, "
        f"{dados.get('localidade', '')}-{dados.get('uf', '')}."
    )
