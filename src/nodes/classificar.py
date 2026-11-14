"""
Nó 2: Classificar — Classifica evento com LLM.
"""

import logging
from ..state import AgentState
from ..llm import LLMClient

logger = logging.getLogger(__name__)


def node(state: AgentState, llm: LLMClient) -> AgentState:
    """
    Classifica evento com LLM.
    
    Extrai tipo, confiança e entidades.
    Se confiança baixa, reanalisa.
    """
    if not state.get("evento"):
        logger.warning("Nenhum evento para classificar")
        return state
    
    logger.info(f"Classificando evento {state['evento_id']}...")
    
    try:
        # Classificação inicial
        tipo, confianca, entidades = llm.classificar_evento(
            state["evento"],
            state.get("cache", {}).get("regras", {})
        )
        
        state["tipo"] = tipo
        state["confianca"] = confianca
        state["entidades"] = entidades
        
        logger.info(f"Tipo: {tipo}, Confiança: {confianca:.2f}")
        
        # Reanalizar se confiança baixa
        if confianca < 0.7:
            logger.warning(f"Confiança baixa ({confianca:.2f}), reanalisando...")
            tipo, confianca, entidades = llm.reanalizar_evento(
                state["evento"],
                f"Confiança inicial baixa ({confianca:.2f})"
            )
            state["tipo"] = tipo
            state["confianca"] = confianca
            state["entidades"] = entidades
            logger.info(f"Reanálise: Tipo: {tipo}, Confiança: {confianca:.2f}")
        
        return state
    
    except Exception as e:
        logger.error(f"Erro ao classificar evento: {e}")
        state["erros"].append(f"classificar: {str(e)}")
        state["tipo"] = "outro"
        state["confianca"] = 0.0
        state["entidades"] = {}
        return state
