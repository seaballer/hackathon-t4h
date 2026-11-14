"""
Testes para os nós do grafo.
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.state import AgentState
from src.nodes import (
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


@pytest.fixture
def base_state():
    """Estado base para testes."""
    return AgentState(
        evento_id="TEST-001",
        evento={},
        encerrado=False,
        erros=[],
        cache={},
        pendencias={},
    )


@pytest.fixture
def mocks():
    """Mocks de dependências."""
    return {
        "mcp": Mock(),
        "llm": Mock(),
        "clock": Mock(),
        "regras": Mock(),
    }


# Testes do Nó 1: Aguardar Evento
def test_aguardar_evento_com_evento(base_state, mocks):
    """Testa aguardar evento quando há evento disponível."""
    mocks["mcp"].proximo_evento.return_value = {
        "evento": {"id": "EVT-001", "assunto": "Teste"},
        "agora": "2024-01-01",
        "encerrado": False,
    }
    
    result = aguardar_evento.node(base_state, mocks["mcp"], mocks["clock"])
    
    assert result["evento_id"] == "EVT-001"
    assert result["evento"]["assunto"] == "Teste"
    assert result["encerrado"] is False


def test_aguardar_evento_encerrado(base_state, mocks):
    """Testa aguardar evento quando encerrado."""
    mocks["mcp"].proximo_evento.return_value = {
        "encerrado": True,
    }
    
    result = aguardar_evento.node(base_state, mocks["mcp"], mocks["clock"])
    
    assert result["encerrado"] is True


def test_aguardar_evento_erro(base_state, mocks):
    """Testa aguardar evento com erro."""
    mocks["mcp"].proximo_evento.side_effect = Exception("Erro MCP")
    
    result = aguardar_evento.node(base_state, mocks["mcp"], mocks["clock"])
    
    assert len(result["erros"]) > 0
    assert "aguardar_evento" in result["erros"][0]


# Testes do Nó 2: Classificar
def test_classificar_evento_valido(base_state, mocks):
    """Testa classificação de evento válido."""
    base_state["evento"] = {"assunto": "Dúvida", "corpo": "..."}
    mocks["llm"].classificar_evento.return_value = (
        "duvida",
        0.95,
        {"patrimonio": None, "colaborador_id": None},
    )
    
    result = classificar.node(base_state, mocks["llm"])
    
    assert result["tipo"] == "duvida"
    assert result["confianca"] == 0.95


def test_classificar_sem_evento(base_state, mocks):
    """Testa classificação sem evento."""
    result = classificar.node(base_state, mocks["llm"])
    
    assert result == base_state


def test_classificar_confianca_baixa(base_state, mocks):
    """Testa reanálise quando confiança baixa."""
    base_state["evento"] = {"assunto": "Teste"}
    mocks["llm"].classificar_evento.return_value = (
        "outro",
        0.5,
        {},
    )
    mocks["llm"].reanalizar_evento.return_value = (
        "duvida",
        0.8,
        {},
    )
    
    result = classificar.node(base_state, mocks["llm"])
    
    assert result["tipo"] == "duvida"
    assert result["confianca"] == 0.8


# Testes do Nó 3: Resolver Dados
def test_resolver_dados_com_patrimonio(base_state, mocks):
    """Testa resolver dados com patrimônio."""
    base_state["entidades"] = {"patrimonio": "PAT-001"}
    mocks["mcp"].consultar_inventario.return_value = {
        "itens": [{"patrimonio": "PAT-001", "status": "disponivel"}]
    }
    
    result = resolver_dados.node(base_state, mocks["mcp"])
    
    assert result["entidades"]["item_atual"]["patrimonio"] == "PAT-001"


def test_resolver_dados_sem_entidades(base_state, mocks):
    """Testa resolver dados sem entidades."""
    result = resolver_dados.node(base_state, mocks["mcp"])
    
    assert result == base_state


# Testes do Nó 4: Montar Plano
def test_montar_plano_duvida(base_state, mocks):
    """Testa montar plano para dúvida."""
    base_state["tipo"] = "duvida"
    base_state["evento_id"] = "EVT-001"
    
    result = montar_plano.node(base_state, mocks["regras"])
    
    assert len(result["plano"]) > 0
    assert result["plano"][0]["tool"] == "responder_evento"


def test_montar_plano_alocacao(base_state, mocks):
    """Testa montar plano para alocação."""
    base_state["tipo"] = "alocacao"
    base_state["evento_id"] = "EVT-001"
    base_state["entidades"] = {"patrimonio": "PAT-001"}
    mocks["regras"].nivel_autonomia.return_value = "FAZ_SOZINHO"
    
    result = montar_plano.node(base_state, mocks["regras"])
    
    assert len(result["plano"]) > 0
    assert result["plano"][0]["tool"] == "alocar_item"


def test_montar_plano_baixa_usa_nivel_de_escala(base_state, mocks):
    base_state["tipo"] = "baixa"
    base_state["evento_id"] = "EVT-001"
    base_state["entidades"] = {"patrimonio": "PAT-001"}
    mocks["regras"].nivel_autonomia.return_value = "ESCALA"

    result = montar_plano.node(base_state, mocks["regras"])

    assert result["plano"][0]["nivel"] == "ESCALA"


def test_montar_plano_evento_desconhecido_escala(base_state, mocks):
    base_state["tipo"] = "outro"
    base_state["evento_id"] = "EVT-001"

    result = montar_plano.node(base_state, mocks["regras"])

    assert result["plano"][0]["nivel"] == "ESCALA"


# Testes do Nó 5: Validar
def test_validar_plano_valido(base_state, mocks):
    """Testa validação de plano válido."""
    base_state["tipo"] = "duvida"
    base_state["plano"] = [
        {
            "tool": "responder_evento",
            "args": {"evento_id": "EVT-001"},
            "motivo": "Responder",
            "nivel": "FAZ_SOZINHO",
        }
    ]
    mocks["regras"].validar_tipo_evento.return_value = (True, "")
    
    result = validar.node(base_state, mocks["regras"])
    
    assert len(result["bloqueios"]) == 0
    assert len(result["plano"]) == 1


def test_validar_plano_com_bloqueios(base_state, mocks):
    """Testa validação com bloqueios."""
    base_state["tipo"] = "alocacao"
    base_state["plano"] = [
        {
            "tool": "alocar_item",
            "args": {"patrimonio": None},
            "motivo": "Alocar",
            "nivel": "FAZ_SOZINHO",
        }
    ]
    mocks["regras"].validar_tipo_evento.return_value = (True, "")
    
    result = validar.node(base_state, mocks["regras"])
    
    assert len(result["bloqueios"]) > 0


# Testes do Nó 6: Aprovar
def test_aprovar_sem_bloqueios(base_state):
    """Testa aprovação sem bloqueios."""
    base_state["bloqueios"] = []
    
    result = aprovar.node(base_state)
    
    assert result["aprovado"] is True


def test_aprovar_com_bloqueios(base_state):
    """Testa aprovação com bloqueios."""
    base_state["bloqueios"] = ["Erro 1", "Erro 2"]
    
    result = aprovar.node(base_state)
    
    assert result["aprovado"] is False


def test_aprovar_nao_executa_acao_que_exige_aprovacao(base_state):
    base_state["bloqueios"] = []
    base_state["plano"] = [
        {"tool": "propor_emprestimo", "nivel": "PROPOE"}
    ]

    result = aprovar.node(base_state)

    assert result["aprovado"] is False
    assert "aprovação humana" in result["bloqueios"][0]


# Testes do Nó 7: Executar
def test_executar_plano_aprovado(base_state, mocks):
    """Testa execução de plano aprovado."""
    base_state["aprovado"] = True
    base_state["plano"] = [
        {
            "tool": "responder_evento",
            "args": {"evento_id": "EVT-001"},
            "motivo": "Responder",
            "nivel": "FAZ_SOZINHO",
        }
    ]
    mocks["mcp"].responder_evento.return_value = {"status": "ok"}
    
    result = executar.node(base_state, mocks["mcp"], mocks["llm"])
    
    assert len(result["acoes_feitas"]) == 1


def test_executar_plano_nao_aprovado(base_state, mocks):
    """Testa execução de plano não aprovado."""
    base_state["aprovado"] = False
    base_state["plano"] = [
        {
            "tool": "responder_evento",
            "args": {"evento_id": "EVT-001"},
        }
    ]
    
    result = executar.node(base_state, mocks["mcp"], mocks["llm"])
    
    assert len(result.get("acoes_feitas", [])) == 0


def test_executar_reserva_kit_seleciona_e_reserva_item(base_state, mocks):
    base_state["aprovado"] = True
    base_state["plano"] = [{
        "tool": "reservar_kit",
        "nivel": "FAZ_SOZINHO",
        "args": {
            "colaborador_id": "C-019",
            "itens": ["notebook"],
        },
    }]
    mocks["mcp"].consultar_inventario.return_value = {
        "itens": [{
            "patrimonio": "EQ-0007",
            "status": "disponível",
            "situacao": "usado",
            "com_quem": "",
        }]
    }

    result = executar.node(base_state, mocks["mcp"], mocks["llm"])

    assert len(result["acoes_feitas"]) == 1
    mocks["mcp"].atualizar.assert_called_once_with(
        "inventario",
        "EQ-0007",
        {"status": "reservado", "com_quem": "C-019"},
        evento_id="TEST-001",
    )


def test_executar_entrada_reserva_kit_padrao_por_area(base_state, mocks):
    base_state["aprovado"] = True
    base_state["plano"] = [{
        "tool": "registrar_entrada",
        "nivel": "FAZ_SOZINHO",
        "args": {"colaborador_id": "C-019"},
    }]
    mocks["mcp"].consultar_colaborador.return_value = {
        "colaborador": {"id": "C-019", "area": "Desenvolvimento"}
    }
    mocks["mcp"].consultar.return_value = {
        "registros": [
            {"regra": "kit_padrao", "valor": ["notebook", "headset"]},
            {"regra": "kit_extra_por_area", "valor": {"Desenvolvimento": ["monitor"]}},
        ]
    }
    mocks["mcp"].consultar_inventario.side_effect = [
        {"itens": [{
            "patrimonio": f"EQ-{index}",
            "status": "disponível",
            "situacao": "novo",
            "com_quem": "",
        }]}
        for index in range(3)
    ]

    result = executar.node(base_state, mocks["mcp"], mocks["llm"])

    assert len(result["acoes_feitas"]) == 1
    assert mocks["mcp"].atualizar.call_count == 3
    assert [call.args[1] for call in mocks["mcp"].atualizar.call_args_list] == [
        "EQ-0",
        "EQ-1",
        "EQ-2",
    ]


def test_executar_entrega_compra_atualiza_itens_em_transito(base_state, mocks):
    base_state["aprovado"] = True
    base_state["plano"] = [{
        "tool": "registrar_entrega_compra",
        "nivel": "FAZ_SOZINHO",
        "args": {"itens": [{"patrimonio": "EQ-0007"}]},
    }]
    mocks["mcp"].consultar_inventario.return_value = {
        "itens": [{
            "patrimonio": "EQ-0007",
            "status": "em_transito",
            "situacao": "",
        }]
    }

    result = executar.node(base_state, mocks["mcp"], mocks["llm"])

    assert len(result["acoes_feitas"]) == 1
    mocks["mcp"].atualizar.assert_called_once_with(
        "inventario",
        "EQ-0007",
        {
            "status": "disponível",
            "situacao": "novo",
            "com_quem": "",
        },
        evento_id="TEST-001",
    )


def test_executar_entrega_compra_nao_finge_cadastro_de_item(base_state, mocks):
    base_state["aprovado"] = True
    base_state["plano"] = [{
        "tool": "registrar_entrega_compra",
        "nivel": "FAZ_SOZINHO",
        "args": {"itens": []},
    }]

    result = executar.node(base_state, mocks["mcp"], mocks["llm"])

    assert result["acoes_feitas"] == []
    assert "não permite registrar novos itens" in result["erros"][0]
    mocks["mcp"].atualizar.assert_not_called()


# Testes do Nó 8: Registrar
def test_registrar_acoes(base_state):
    """Testa registro de ações."""
    base_state["acoes_feitas"] = [
        {"tool": "responder_evento", "resultado": "ok"}
    ]
    
    result = registrar.node(base_state)
    
    assert result == base_state


# Testes do Nó 9: Responder
def test_responder_com_acoes(base_state, mocks):
    """Testa resposta com ações executadas."""
    base_state["acoes_feitas"] = [
        {"tool": "responder_evento", "resultado": "ok"}
    ]
    base_state["tipo"] = "duvida"
    mocks["llm"].redigir_resposta.return_value = "Resposta redigida"
    
    result = responder.node(base_state, mocks["llm"], mocks["mcp"])
    
    assert result["resposta_remetente"] == "Resposta redigida"
    mocks["mcp"].responder_evento.assert_called_once_with(
        "TEST-001",
        "Resposta redigida",
        motivo="Resposta final do agente",
    )


def test_responder_sem_acoes(base_state, mocks):
    """Testa resposta sem ações."""
    base_state["acoes_feitas"] = []
    
    result = responder.node(base_state, mocks["llm"], mocks["mcp"])
    
    assert "resposta_remetente" in result
    mocks["mcp"].responder_evento.assert_called_once_with(
        "TEST-001",
        "Sua solicitação foi recebida e será processada.",
        motivo="Resposta final do agente",
    )


def test_responder_nao_confirma_quando_acao_falha(base_state, mocks):
    base_state["plano"] = [{"tool": "alocar_item"}]
    base_state["acoes_feitas"] = []

    result = responder.node(base_state, mocks["llm"], mocks["mcp"])

    assert result["resposta_remetente"] == ""
    mocks["mcp"].responder_evento.assert_not_called()
