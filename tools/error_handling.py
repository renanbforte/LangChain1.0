# =============================================================================
# tools/error_handling.py  —  Tratamento de erro CENTRAL para TODAS as tools
# -----------------------------------------------------------------------------
# No LangChain 1.0, wrap_tool_call virou um MIDDLEWARE: em vez de repetir
# try/except dentro de cada tool, definimos UM interceptador que envolve a
# execução de QUALQUER tool. Se a tool falhar, ele devolve uma ToolMessage com
# uma mensagem amigável, e o agente segue a conversa em vez de o programa quebrar.
#
# Isto é "separação de responsabilidades" no nível do agente: as tools cuidam
# do trabalho delas; o tratamento de falhas mora em um lugar só.
# =============================================================================

from langchain.agents.middleware import wrap_tool_call   # cria o middleware
from langchain_core.messages import ToolMessage           # a "resposta de tool" ao agente

# Importamos o NOSSO tipo de erro para tratá-lo de forma especial.
from ._shared import ToolExternaError


# @wrap_tool_call transforma esta função em um AgentMiddleware.
# A função recebe:
#   request -> descreve a chamada da tool (inclui request.tool_call com "id" e "args")
#   handler -> a função que REALMENTE executa a tool; chamamos handler(request).
@wrap_tool_call
def tratar_erros_de_tool(request, handler):
    """Envolve toda execução de tool e converte falhas em mensagens amigáveis."""
    try:
        # handler(request) executa a tool de verdade e devolve a ToolMessage.
        return handler(request)
    except ToolExternaError as e:
        # Erro ESPERADO (rede, CEP inexistente, etc.): devolvemos uma ToolMessage
        # explicando o problema. O agente recebe isso como "resultado da tool" e
        # pode responder ao usuário com jeito (ex.: "não achei esse CEP").
        #   content        -> o texto do erro que o agente vai ler.
        #   tool_call_id   -> amarra esta resposta à chamada específica da tool.
        return ToolMessage(
            content=f"A ferramenta falhou: {e}",
            tool_call_id=request.tool_call["id"],
        )
    except Exception as e:
        # Erro INESPERADO (um bug de verdade). Também devolvemos uma mensagem em
        # vez de derrubar o agente, mas deixando claro que foi algo não previsto.
        return ToolMessage(
            content=f"Erro inesperado na ferramenta: {e}",
            tool_call_id=request.tool_call["id"],
        )
