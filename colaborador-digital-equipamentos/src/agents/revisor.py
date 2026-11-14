"""
Agente Revisor: valida regras, atribui nível, bloqueia e-mail externo, detecta duplicidade.
"""

import logging
from typing import Dict, Any
from ..state import AgentState
from ..rules import RegrasEquipamentos

logger = logging.getLogger(__name__)


def revisor(state: AgentState, regras: RegrasEquipamentos) -> AgentState:
    """
    Revisor: valida plano, atribui nível final, detecta bloqueios.

    Responsabilidades:
    - Validar regras de negócio
    - Atribuir nível final (FAZ/PROPÕE/ESCALA)
    - Bloquear e-mail externo
    - Detectar duplicidade
    """

    if not state.get("plano"):
        logger.warning("Revisor: sem plano para revisar")
        state["plano_aprovado"] = []
        state["nivel_final"] = "ESCALA"
        state["bloqueios"] = ["Sem plano de ações"]
        return state

    logger.info(f"Revisor analisando plano para {state['evento_id']}")

    bloqueios: list[str] = []
    plano_aprovado = []
    nivel_maximo = "FAZ_SOZINHO"

    try:
        # 1. Bloquear e-mail externo
        if state.get("origem") == "email_externo":
            bloqueios.append(
                "Evento de e-mail externo bloqueado por segurança")
            state["plano_aprovado"] = []
            state["nivel_final"] = "ESCALA"
            state["bloqueios"] = bloqueios
            return state

        # 2. Validar cada ação do plano
        for acao in state["plano"]:
            valida, motivo = _validar_acao(acao, state, regras)

            if not valida:
                bloqueios.append(f"Ação {acao['tool']}: {motivo}")
                continue

            # Ação válida, adicionar ao plano aprovado
            plano_aprovado.append(acao)

            # Atualizar nível máximo
            nivel_acao = acao.get("nivel", "ESCALA")
            if _comparar_niveis(nivel_acao, nivel_maximo) > 0:
                nivel_maximo = nivel_acao

        # 3. Detectar duplicidade (simplificado)
        # Em produção, consultaria um banco de dados

        # 4. Atribuir nível final
        state["plano_aprovado"] = plano_aprovado
        state["nivel_final"] = nivel_maximo
        state["bloqueios"] = bloqueios

        logger.info(
            f"Plano aprovado: {len(plano_aprovado)} ações, nível: {nivel_maximo}")

        if bloqueios:
            logger.warning(f"Bloqueios detectados: {bloqueios}")

        return state

    except Exception as e:
        logger.error(f"Erro no Revisor: {e}")
        state["erros"].append(str(e))
        state["plano_aprovado"] = []
        state["nivel_final"] = "ESCALA"
        state["bloqueios"] = [str(e)]
        return state


def _validar_acao(acao: Dict[str, Any], state: AgentState,
                  regras: RegrasEquipamentos) -> tuple[bool, str]:
    """Valida uma ação individual."""

    tool = acao.get("tool", "")
    args = acao.get("args", {})

    # Validações específicas por tool
    if tool == "atualizar_inventario":
        patrimonio = args.get("patrimonio")
        if not patrimonio:
            return False, "Patrimonio não informado"

        novo_status = args.get("status")
        if novo_status:
            valido, msg = regras.validar_status_inventario(novo_status)
            if not valido:
                return False, msg

    elif tool == "responder_evento":
        evento_id = args.get("evento_id")
        if not evento_id:
            return False, "Evento ID não informado"

    elif tool == "enviar_mensagem":
        destinatario = args.get("destinatario")
        if not destinatario:
            return False, "Destinatário não informado"

    elif tool == "registrar":
        base = args.get("base")
        if not base:
            return False, "Base não informada"

    elif tool == "consultar_inventario":
        # Sempre válido
        pass

    else:
        return False, f"Tool desconhecida: {tool}"

    return True, ""


def _comparar_niveis(nivel1: str, nivel2: str) -> int:
    """
    Compara dois níveis de autonomia.
    Retorna: 1 se nivel1 > nivel2, -1 se nivel1 < nivel2, 0 se iguais.
    Ordem: FAZ_SOZINHO < PROPOE < ESCALA
    """
    ordem = {"FAZ_SOZINHO": 0, "PROPOE": 1, "ESCALA": 2}
    val1 = ordem.get(nivel1, 2)
    val2 = ordem.get(nivel2, 2)

    if val1 > val2:
        return 1
    elif val1 < val2:
        return -1
    else:
        return 0
