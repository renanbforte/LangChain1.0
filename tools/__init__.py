# =============================================================================
# tools/__init__.py  —  O REGISTRO CENTRAL de todas as tools
# -----------------------------------------------------------------------------
# Este arquivo transforma a pasta "tools/" em um PACOTE Python e serve de
# "vitrine": ele reúne todas as tools numa lista única (TOOLS) e o middleware
# de erro, para o agente importar UMA coisa só e não conhecer os detalhes.
#
# Assim, o agente faz apenas:
#     from tools import TOOLS, tratar_erros_de_tool
# ...e não precisa saber em quais arquivos cada tool mora. Se amanhã você
# reorganizar os arquivos internos, o agente NEM percebe. Isso se chama
# "baixo acoplamento": o agente depende da vitrine, não das prateleiras.
# =============================================================================

# Importamos cada tool do seu arquivo de domínio.
from .temperatura import converter_temperatura   # tool de cálculo
from .cep import buscar_cep                       # tool de API (ViaCEP)

# Importamos o middleware de tratamento de erro (definido em error_handling.py).
from .error_handling import tratar_erros_de_tool


# -----------------------------------------------------------------------------
# A LISTA que o agente vai receber em create_agent(tools=TOOLS).
# -----------------------------------------------------------------------------
# >>> PARA ADICIONAR UMA NOVA TOOL NO FUTURO:
# >>>   1. Crie o arquivo do domínio (ex.: tools/cotacao.py) com schema+service+@tool.
# >>>   2. Importe a tool aqui em cima:  from .cotacao import buscar_cotacao
# >>>   3. Inclua-a na lista abaixo.
# É o ÚNICO lugar que você edita para "ligar" uma tool nova ao agente.
TOOLS = [
    converter_temperatura,
    buscar_cep,
    # nova_tool,   # <- adicione aqui
]

# __all__ define o que é "público" do pacote (o que aparece num import *).
# É documentação viva: diz "use TOOLS e tratar_erros_de_tool; o resto é interno".
__all__ = ["TOOLS", "tratar_erros_de_tool"]
