"""
Nó 8: Registrar — Registra resultados das ações executadas.
"""

import logging
from ..state import AgentState

logger = logging.getLogger(__name__)


def node(state: AgentState) -> AgentState:
    """
    Registra ações feitas.
    
    Log informativo do que foi executado.
    """
    evento_id = state.get("evento_id", "")
    acoes_feitas = state.get("acoes_feitas", [])
    bloqueios = state.get("bloqueios", [])
    
    logger.info(f"Registrando resultados para evento {evento_id}")
    logger.info(f"  - Ações executadas: {len(acoes_feitas)}")
    logger.info(f"  - Bloqueios: {len(bloqueios)}")
    
    if acoes_feitas:
        for acao in acoes_feitas:
            logger.debug(f"    - {acao.get('tool')}: {acao.get('resultado')}")
    
    if bloqueios:
        for bloqueio in bloqueios:
            logger.debug(f"    - Bloqueio: {bloqueio}")
    
    return state
