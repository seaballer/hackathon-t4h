"""
Agente Coordenador: laço principal, tick diário, backlog scan, roteamento.
"""

import logging
from typing import Dict, Any
from ..state import AgentState
from ..mcp_client import MCPClient
from ..clock import Clock

logger = logging.getLogger(__name__)


def coordenador(state: AgentState, mcp: MCPClient, clock: Clock) -> AgentState:
    """
    Coordenador: gerencia o laço principal.

    Responsabilidades:
    - Chamar proximo_evento em laço
    - Detectar virada de dia e disparar tick diário
    - Fazer scan de backlog
    - Rotear para Analista
    - Detectar encerramento (encerrado=true)
    """

    logger.info("Coordenador iniciado")

    # Inicializar estado se necessário
    if "cache" not in state or not state["cache"]:
        state["cache"] = {
            "regras": {},
            "catalogo": {},
            "colaboradores": {}
        }

    if "pendencias" not in state or not state["pendencias"]:
        state["pendencias"] = {
            "devolucoes": [],
            "compras_em_transito": [],
            "aprovacoes": [],
            "emprestimos": []
        }

    if "acoes_feitas" not in state:
        state["acoes_feitas"] = []

    if "erros" not in state:
        state["erros"] = []

    try:
        # Obter próximo evento
        logger.info("Aguardando próximo evento...")
        resposta = mcp.proximo_evento(esperar_segundos=30)

        # Verificar se cenário encerrou
        if resposta.get("encerrado"):
            logger.info("Cenário encerrado")
            state["encerrado"] = True
            return state

        # Processar evento se houver
        if resposta.get("evento"):
            evento = resposta["evento"]
            state["evento_id"] = evento.get("id", "")
            state["evento"] = evento
            state["origem"] = evento.get("origem", "cenario")
            state["data_simulada"] = resposta.get("agora", "")

            logger.info(
                f"Evento recebido: {state['evento_id']} ({state['origem']})")

            # Rotear para Analista
            state["tipo"] = ""
            state["entidades"] = {}
            state["plano"] = []

            return state

        else:
            # Sem evento novo, mas relógio avançou
            logger.info(
                f"Sem evento novo. Próximo em {resposta.get('proximo_em', 'desconhecido')}")
            state["evento"] = None

            # Verificar se virou dia (tick diário)
            data_nova = resposta.get("agora", "")
            if data_nova and data_nova != state.get("data_simulada"):
                logger.info(f"Virada de dia detectada: {data_nova}")
                state["data_simulada"] = data_nova
                # Tick diário será processado em próxima iteração

            return state

    except Exception as e:
        logger.error(f"Erro no Coordenador: {e}")
        state["erros"].append(str(e))
        return state
