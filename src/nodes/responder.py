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
        if len(acoes_feitas) < len(state.get("plano", [])):
            logger.error("Resposta não enviada porque uma ou mais ações falharam")
            state["resposta_remetente"] = ""
            return state

        # Se não há ações feitas, resposta padrão
        if not acoes_feitas:
            resposta = "Sua solicitação foi recebida e será processada."
        else:
            # Redigir resposta com LLM
            try:
                resposta = llm.redigir_resposta(
                    state.get("tipo", ""),
                    state.get("entidades", {}),
                    {"acoes": len(acoes_feitas)}
                )
                logger.info("Resposta redigida com sucesso")
            except Exception as e:
                logger.warning(f"Erro ao redigir resposta: {e}")
                resposta = f"Sua solicitação foi processada ({len(acoes_feitas)} ações)."

        state["resposta_remetente"] = resposta
        if evento_id:
            try:
                mcp.responder_evento(
                    evento_id,
                    resposta,
                    motivo="Resposta final do agente",
                )
                logger.info("Resposta enviada ao MCP")
            except Exception as e:
                logger.error(f"Erro ao enviar resposta ao MCP: {e}")
                state["erros"].append(f"responder MCP: {str(e)}")
                state["resposta_remetente"] = ""
        
        return state
    
    except Exception as e:
        logger.error(f"Erro ao preparar resposta: {e}")
        state["erros"].append(f"responder: {str(e)}")
        state["resposta_remetente"] = ""
        return state
