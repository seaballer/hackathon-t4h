"""
Grafo LangGraph: orquestração com 9 nós.
"""

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END  # type : ignore
try:
    from langgraph_checkpoint.sqlite import SqliteSaver
except ImportError:
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError:
        SqliteSaver = None

from .state import AgentState
from .nodes import (
    aguardar_evento,
    classificar,
    resolver_dados,
    montar_plano,
    validar,
    aprovar,
    executar,
    registrar,
    responder,
)
from .mcp_client import MCPClient
from .llm import LLMClient
from .clock import Clock
from .rules import RegrasEquipamentos

logger = logging.getLogger(__name__)


def criar_grafo(mcp: MCPClient, llm: LLMClient, clock: Clock,
                regras: RegrasEquipamentos, checkpoint_dir: str = ".checkpoints"):
    """
    Cria o grafo LangGraph com 9 nós.

    Fluxo:
    1. Aguardar Evento
    2. Classificar
    3. Resolver Dados
    4. Montar Plano
    5. Validar
    6. Aprovar
    7. Executar
    8. Registrar
    9. Responder
    ↓
    Volta ao 1

    Args:
        mcp: cliente MCP
        llm: cliente LLM
        clock: relógio simulado
        regras: regras de negócio
        checkpoint_dir: diretório para checkpoints SQLite
    """

    # Criar grafo
    workflow = StateGraph(AgentState)

    # Adicionar nós
    workflow.add_node("aguardar_evento",
                     lambda s: aguardar_evento.node(s, mcp, clock))
    workflow.add_node("classificar",
                     lambda s: classificar.node(s, llm))
    workflow.add_node("resolver_dados",
                     lambda s: resolver_dados.node(s, mcp))
    workflow.add_node("montar_plano",
                     lambda s: montar_plano.node(s, regras))
    workflow.add_node("validar",
                     lambda s: validar.node(s, regras))
    workflow.add_node("aprovar",
                     lambda s: aprovar.node(s))
    workflow.add_node("executar",
                     lambda s: executar.node(s, mcp, llm))
    workflow.add_node("registrar",
                     lambda s: registrar.node(s))
    workflow.add_node("responder",
                     lambda s: responder.node(s, llm, mcp))

    # Definir fluxo
    workflow.set_entry_point("aguardar_evento")

    # Transições condicionais
    def deve_classificar(state: AgentState) -> str:
        """Após aguardar evento: classificar ou encerrar."""
        if state.get("encerrado"):
            return END
        if state.get("evento"):
            return "classificar"
        return "aguardar_evento"

    workflow.add_conditional_edges("aguardar_evento", deve_classificar)

    # Fluxo linear: classificar -> resolver -> montar -> validar -> aprovar
    workflow.add_edge("classificar", "resolver_dados")
    workflow.add_edge("resolver_dados", "montar_plano")
    workflow.add_edge("montar_plano", "validar")
    workflow.add_edge("validar", "aprovar")

    # Após aprovar: executar ou voltar
    def deve_executar(state: AgentState) -> str:
        """Após aprovar: executar se aprovado, senão voltar."""
        if state.get("aprovado"):
            return "executar"
        return "aguardar_evento"

    workflow.add_conditional_edges("aprovar", deve_executar)

    # Fluxo linear: executar -> registrar -> responder
    workflow.add_edge("executar", "registrar")
    workflow.add_edge("registrar", "responder")

    # Após responder: voltar ao início
    workflow.add_edge("responder", "aguardar_evento")

    # Compilar com checkpoint
    if SqliteSaver is not None:
        checkpointer = SqliteSaver(checkpoint_dir)
        graph = workflow.compile(checkpointer=checkpointer)
    else:
        graph = workflow.compile()

    logger.info("Grafo LangGraph criado com 9 nós")

    return graph
