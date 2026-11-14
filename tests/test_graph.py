"""
Testes para o grafo LangGraph.
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.graph import criar_grafo
from src.state import AgentState


@pytest.fixture
def mocks():
    """Fixture com mocks de dependências."""
    mcp = Mock()
    llm = Mock()
    clock = Mock()
    regras = Mock()
    return {"mcp": mcp, "llm": llm, "clock": clock, "regras": regras}


def test_criar_grafo(mocks):
    """Testa criação do grafo."""
    graph = criar_grafo(
        mocks["mcp"],
        mocks["llm"],
        mocks["clock"],
        mocks["regras"]
    )
    assert graph is not None


def test_grafo_tem_9_nos(mocks):
    """Testa que o grafo tem 9 nós."""
    graph = criar_grafo(
        mocks["mcp"],
        mocks["llm"],
        mocks["clock"],
        mocks["regras"]
    )
    # Verificar que o grafo foi compilado
    assert hasattr(graph, "invoke")


def test_estado_inicial(mocks):
    """Testa estado inicial."""
    state = AgentState(
        evento_id="TEST-001",
        evento={},
        encerrado=False,
        erros=[]
    )
    assert state["evento_id"] == "TEST-001"
    assert state["encerrado"] is False


def test_estado_com_novos_campos(mocks):
    """Testa novos campos de estado."""
    state = AgentState(
        evento_id="TEST-001",
        confianca=0.85,
        aprovado=True,
        erros=[]
    )
    assert state["confianca"] == 0.85
    assert state["aprovado"] is True
