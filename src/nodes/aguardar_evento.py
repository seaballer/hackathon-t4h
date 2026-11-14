"""
Nó 1: Aguardar Evento — Aguarda próximo evento do MCP.
"""

import logging
from ..state import AgentState
from ..mcp_client import MCPClient
from ..clock import Clock

logger = logging.getLogger(__name__)


def node(state: AgentState, mcp: MCPClient, clock: Clock) -> AgentState:
    """
    Aguarda próximo evento do MCP.
    
    Se encerrado, marca estado como encerrado.
    Se há evento, armazena no estado.
    """
    logger.info("Aguardando próximo evento...")
    
    try:
        resposta = mcp.proximo_evento(esperar_segundos=30)
        
        if resposta.get("encerrado"):
            logger.info("Encerramento solicitado")
            state["encerrado"] = True
            return state
        
        if resposta.get("evento"):
            evento = resposta["evento"]
            state["evento_id"] = evento.get("id", "")
            state["evento"] = evento
            state["data_simulada"] = resposta.get("agora", "")
            logger.info(f"Evento recebido: {state['evento_id']}")
        else:
            logger.debug("Nenhum evento disponível")
        
        return state
    
    except Exception as e:
        logger.error(f"Erro ao aguardar evento: {e}")
        state["erros"].append(f"aguardar_evento: {str(e)}")
        return state
