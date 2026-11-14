"""
Nó 9: Responder — Envia resposta ao remetente.
"""

import logging
from ..state import AgentState
from ..llm import LLMClient
from ..mcp_client import MCPClient

logger = logging.getLogger(__name__)


def node(state: AgentState, llm: LLMClient, mcp: MCPClient) -> AgentState:
    """
    Envia resposta ao remetente.
    
    Redige resposta baseada nas ações executadas.
    """
    evento_id = state.get("evento_id", "")
    acoes_feitas = state.get("acoes_feitas", [])
    
    logger.info(f"Preparando resposta para evento {evento_id}...")
    
    try:
        # Se não há ações feitas, resposta padrão
        if not acoes_feitas:
            resposta = "Sua solicitação foi recebida e será processada."
            state["resposta_remetente"] = resposta
            logger.info("Resposta padrão enviada")
            return state
        
        # Redigir resposta com LLM
        try:
            resposta = llm.redigir_resposta(
                state.get("tipo", ""),
                state.get("entidades", {}),
                {"acoes": len(acoes_feitas)}
            )
            state["resposta_remetente"] = resposta
            logger.info("Resposta redigida com sucesso")
        except Exception as e:
            logger.warning(f"Erro ao redigir resposta: {e}")
            resposta = f"Sua solicitação foi processada ({len(acoes_feitas)} ações)."
            state["resposta_remetente"] = resposta
        
        return state
    
    except Exception as e:
        logger.error(f"Erro ao preparar resposta: {e}")
        state["erros"].append(f"responder: {str(e)}")
        state["resposta_remetente"] = "Sua solicitação foi processada."
        return state
