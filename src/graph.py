"""
Grafo LangGraph: orquestração dos agentes.
"""

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .state import AgentState
from .agents import coordenador, analista, revisor, executor
from .mcp_client import MCPClient
from .llm import LLMClient
from .clock import Clock
from .rules import RegrasEquipamentos

logger = logging.getLogger(__name__)


def criar_grafo(mcp: MCPClient, llm: LLMClient, clock: Clock,
                regras: RegrasEquipamentos, checkpoint_dir: str = ".checkpoints"):
    """
    Cria o grafo LangGraph com os agentes.

    Args:
        mcp: cliente MCP
        llm: cliente LLM
        clock: relógio simulado
        regras: regras de negócio
        checkpoint_dir: diretório para checkpoints SQLite
    """

    # Criar grafo
    workflow = StateGraph(AgentState)

    # Definir nós
    def node_coordenador(state: AgentState) -> AgentState:
        return coordenador(state, mcp, clock)

    def node_analista(state: AgentState) -> AgentState:
        return analista(state, llm, mcp, regras)

    def node_revisor(state: AgentState) -> AgentState:
        return revisor(state, regras)

    def node_executor(state: AgentState) -> AgentState:
        return executor(state, mcp, llm)

    # Adicionar nós ao grafo
    workflow.add_node("coordenador", node_coordenador)
    workflow.add_node("analista", node_analista)
    workflow.add_node("revisor", node_revisor)
    workflow.add_node("executor", node_executor)

    # Definir fluxo
    workflow.set_entry_point("coordenador")

    # Coordenador -> Analista (se há evento)
    def deve_analisar(state: AgentState) -> str:
        if state.get("encerrado"):
            return END
        if state.get("evento"):
            return "analista"
        return "coordenador"

    workflow.add_conditional_edges("coordenador", deve_analisar)

    # Analista -> Revisor
    workflow.add_edge("analista", "revisor")

    # Revisor -> Executor (se plano aprovado)
    def deve_executar(state: AgentState) -> str:
        if state.get("plano_aprovado"):
            return "executor"
        return "coordenador"

    workflow.add_conditional_edges("revisor", deve_executar)

    # Executor -> Coordenador (laço)
    workflow.add_edge("executor", "coordenador")

    # Compilar com checkpoint
    checkpointer = SqliteSaver(checkpoint_dir)
    graph = workflow.compile(checkpointer=checkpointer)

    logger.info("Grafo LangGraph criado com sucesso")

    return graph
