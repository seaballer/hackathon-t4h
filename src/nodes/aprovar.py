"""
Nó 6: Aprovar — Decide se aprova execução do plano.
"""

import logging
from ..state import AgentState

logger = logging.getLogger(__name__)


def node(state: AgentState) -> AgentState:
    """
    Decide se aprova execução do plano.
    
    Se há bloqueios, não aprova.
    Caso contrário, aprova.
    """
    logger.info(f"Analisando aprovação para evento {state['evento_id']}...")
    
    bloqueios = list(state.get("bloqueios", []))
    for acao in state.get("plano", []):
        nivel = acao.get("nivel")
        if nivel != "FAZ_SOZINHO":
            bloqueios.append(
                f"{acao.get('tool', 'ação')}: nível {nivel or 'não definido'} "
                "requer aprovação humana; fila de aprovação indisponível."
            )
    state["bloqueios"] = bloqueios
    
    if bloqueios:
        state["aprovado"] = False
        logger.warning(f"Plano não aprovado: {len(bloqueios)} bloqueios")
    else:
        state["aprovado"] = True
        logger.info("Plano aprovado para execução")
    
    return state
