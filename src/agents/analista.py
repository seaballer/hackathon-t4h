"""
Agente Analista: extrai intenção + entidades, resolve dados, monta plano de ações.
"""

import logging
from typing import Dict, Any
from ..state import AgentState, PlanoAcao
from ..llm import LLMClient
from ..mcp_client import MCPClient
from ..rules import RegrasEquipamentos

logger = logging.getLogger(__name__)


def analista(state: AgentState, llm: LLMClient, mcp: MCPClient,
             regras: RegrasEquipamentos) -> AgentState:
    """
    Analista: classifica evento, extrai entidades, monta plano.

    Responsabilidades:
    - Chamar LLM para classificar intenção + extrair entidades
    - Resolver colaborador_id, patrimonio, data, itens
    - Montar plano de ações com níveis
    """

    if not state.get("evento"):
        logger.warning("Analista: sem evento para processar")
        return state

    logger.info(f"Analista processando evento {state['evento_id']}")

    try:
        evento = state["evento"]

        # 1. Classificar evento com LLM
        logger.info("Classificando evento com LLM...")
        tipo, confianca, entidades = llm.classificar_evento(
            evento,
            state.get("cache", {}).get("regras", {})
        )

        state["tipo"] = tipo
        state["entidades"] = entidades

        logger.info(f"Tipo: {tipo}, Confiança: {confianca}")

        # 2. Se confiança baixa, reanalizar
        if confianca < 0.7:
            logger.warning(f"Confiança baixa ({confianca}), reanalisa ndo...")
            tipo, confianca, entidades = llm.reanalizar_evento(
                evento,
                f"Confiança inicial baixa ({confianca})"
            )
            state["tipo"] = tipo
            state["entidades"] = entidades

        # 3. Resolver entidades consultando MCP
        logger.info("Resolvendo entidades...")

        # Consultar inventário se há patrimonio
        if entidades.get("patrimonio"):
            try:
                inv = mcp.consultar_inventario({
                    "patrimonio": entidades["patrimonio"]
                })
                if inv.get("itens"):
                    entidades["item_atual"] = inv["itens"][0]
            except Exception as e:
                logger.warning(f"Erro ao consultar inventário: {e}")

        # 4. Montar plano de ações
        logger.info("Montando plano de ações...")
        plano = _montar_plano(tipo, entidades, regras, state)
        state["plano"] = plano

        logger.info(f"Plano montado com {len(plano)} ações")

        return state

    except Exception as e:
        logger.error(f"Erro no Analista: {e}")
        state["erros"].append(str(e))
        state["tipo"] = "outro"
        state["entidades"] = {}
        state["plano"] = []
        return state


def _montar_plano(tipo: str, entidades: Dict[str, Any],
                  regras: RegrasEquipamentos, state: AgentState) -> list:
    """Monta o plano de ações baseado no tipo de evento."""

    plano: list[PlanoAcao] = []

    if tipo == "duvida":
        plano.append({
            "tool": "responder_evento",
            "args": {"evento_id": state["evento_id"]},
            "motivo": "Responder dúvida com template",
            "nivel": "FAZ_SOZINHO"
        })

    elif tipo == "consulta_estoque":
        plano.append({
            "tool": "consultar_inventario",
            "args": {"status": "disponivel"},
            "motivo": "Consultar estoque disponível",
            "nivel": "FAZ_SOZINHO"
        })
        plano.append({
            "tool": "responder_evento",
            "args": {"evento_id": state["evento_id"]},
            "motivo": "Responder com contagem",
            "nivel": "FAZ_SOZINHO"
        })

    elif tipo == "devolucao":
        plano.append({
            "tool": "atualizar_inventario",
            "args": {
                "patrimonio": entidades.get("patrimonio"),
                "status": "disponivel"
            },
            "motivo": "Marcar item como disponível",
            "nivel": "FAZ_SOZINHO"
        })
        plano.append({
            "tool": "responder_evento",
            "args": {"evento_id": state["evento_id"]},
            "motivo": "Confirmar devolução",
            "nivel": "FAZ_SOZINHO"
        })

    elif tipo == "alocacao" or tipo == "reserva_kit":
        tem_estoque = entidades.get("item_atual", {}).get(
            "status") == "disponivel"
        valor = entidades.get("valor", 0.0)

        nivel = regras.nivel_autonomia(tipo, valor, tem_estoque)

        plano.append({
            "tool": "atualizar_inventario",
            "args": {
                "patrimonio": entidades.get("patrimonio"),
                "status": "reservado"
            },
            "motivo": "Reservar item",
            "nivel": nivel
        })
        plano.append({
            "tool": "responder_evento",
            "args": {"evento_id": state["evento_id"]},
            "motivo": "Confirmar alocação",
            "nivel": nivel
        })

    elif tipo == "troca_defeito":
        plano.append({
            "tool": "atualizar_inventario",
            "args": {
                "patrimonio": entidades.get("patrimonio"),
                "status": "danificado"
            },
            "motivo": "Marcar item como danificado",
            "nivel": "FAZ_SOZINHO"
        })
        plano.append({
            "tool": "responder_evento",
            "args": {"evento_id": state["evento_id"]},
            "motivo": "Confirmar troca",
            "nivel": "FAZ_SOZINHO"
        })

    elif tipo == "emprestimo":
        plano.append({
            "tool": "atualizar_inventario",
            "args": {
                "patrimonio": entidades.get("patrimonio"),
                "status": "emprestado"
            },
            "motivo": "Registrar empréstimo",
            "nivel": "PROPOE"
        })

    elif tipo == "entrada_pessoa":
        plano.append({
            "tool": "registrar",
            "args": {
                "base": "alocacoes",
                "dados": {
                    "colaborador_id": entidades.get("colaborador_id"),
                    "data": entidades.get("data"),
                    "evento_id": state["evento_id"]
                }
            },
            "motivo": "Registrar entrada de pessoa",
            "nivel": "FAZ_SOZINHO"
        })

    elif tipo == "saida_pessoa":
        plano.append({
            "tool": "enviar_mensagem",
            "args": {
                "destinatario": entidades.get("colaborador_id"),
                "assunto": "Devolução de equipamentos",
                "evento_id": state["evento_id"]
            },
            "motivo": "Cobrar devolução",
            "nivel": "FAZ_SOZINHO"
        })

    elif tipo == "baixa":
        plano.append({
            "tool": "atualizar_inventario",
            "args": {
                "patrimonio": entidades.get("patrimonio"),
                "status": "baixado"
            },
            "motivo": "Baixar item",
            "nivel": "ESCALA"
        })

    else:  # "outro" ou desconhecido
        plano.append({
            "tool": "responder_evento",
            "args": {"evento_id": state["evento_id"]},
            "motivo": "Evento incerto, requer análise",
            "nivel": "ESCALA"
        })

    return plano
