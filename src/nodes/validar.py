"""
Nó 5: Validar — Valida plano contra regras de negócio.
"""

import logging
from typing import List, Tuple
from ..state import AgentState, PlanoAcao
from ..rules import RegrasEquipamentos

logger = logging.getLogger(__name__)


def _validar_acao(acao: PlanoAcao, state: AgentState, 
                  regras: RegrasEquipamentos) -> Tuple[bool, str]:
    """
    Valida uma ação contra as regras.
    
    Returns:
        (válida, motivo_bloqueio)
    """
    tool = acao.get("tool", "")
    args = acao.get("args", {})
    
    # Validar tipo de evento
    tipo = state.get("tipo", "")
    valido, msg = regras.validar_tipo_evento(tipo)
    if not valido:
        return False, msg
    
    # Validar patrimônio se necessário
    if "patrimonio" in args:
        patrimonio = args.get("patrimonio")
        if not patrimonio:
            return False, "Patrimônio não informado"
    
    # Validar colaborador se necessário
    if "colaborador_id" in args:
        colaborador_id = args.get("colaborador_id")
        if not colaborador_id:
            return False, "Colaborador não informado"
    
    # Validar itens se necessário
    if "itens" in args:
        itens = args.get("itens", [])
        if not itens:
            return False, "Itens não informados"
    
    return True, ""


def node(state: AgentState, regras: RegrasEquipamentos) -> AgentState:
    """
    Valida plano contra regras de negócio.
    
    Remove ações inválidas e registra bloqueios.
    """
    logger.info(f"Validando plano para evento {state['evento_id']}...")
    
    bloqueios: List[str] = []
    plano_valido: List[PlanoAcao] = []
    
    try:
        for acao in state.get("plano", []):
            valida, motivo = _validar_acao(acao, state, regras)
            if not valida:
                bloqueios.append(f"{acao.get('tool', 'unknown')}: {motivo}")
                logger.warning(f"Ação bloqueada: {acao.get('tool')} - {motivo}")
            else:
                plano_valido.append(acao)
        
        state["plano"] = plano_valido
        state["bloqueios"] = bloqueios
        
        if bloqueios:
            logger.warning(f"Plano tem {len(bloqueios)} bloqueios")
        else:
            logger.info("Plano validado com sucesso")
        
        return state
    
    except Exception as e:
        logger.error(f"Erro ao validar plano: {e}")
        state["erros"].append(f"validar: {str(e)}")
        state["bloqueios"] = [f"Erro na validação: {str(e)}"]
        return state
