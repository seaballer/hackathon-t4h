"""
Testes para o módulo de regras.
"""

import pytest
from src.rules import RegrasEquipamentos


@pytest.fixture
def regras():
    """Fixture com instância de regras."""
    return RegrasEquipamentos({})


def test_validar_tipo_evento_valido(regras):
    """Testa validação de tipo de evento válido."""
    valido, msg = regras.validar_tipo_evento("duvida")
    assert valido is True
    assert msg == ""


def test_validar_tipo_evento_invalido(regras):
    """Testa validação de tipo de evento inválido."""
    valido, msg = regras.validar_tipo_evento("tipo_inexistente")
    assert valido is False
    assert "desconhecido" in msg.lower()


def test_validar_status_inventario_valido(regras):
    """Testa validação de status válido."""
    valido, msg = regras.validar_status_inventario("disponivel")
    assert valido is True
    assert msg == ""


def test_validar_status_inventario_invalido(regras):
    """Testa validação de status inválido."""
    valido, msg = regras.validar_status_inventario("status_invalido")
    assert valido is False
    assert "inválido" in msg.lower()


def test_pode_comprar_autonomamente(regras):
    """Testa limite de compra autônoma."""
    assert regras.pode_comprar_autonomamente(400.0) is True
    assert regras.pode_comprar_autonomamente(500.0) is True
    assert regras.pode_comprar_autonomamente(600.0) is False


def test_nivel_autonomia_duvida(regras):
    """Testa nível de autonomia para dúvida."""
    nivel = regras.nivel_autonomia("duvida")
    assert nivel == "FAZ_SOZINHO"


def test_nivel_autonomia_emprestimo(regras):
    """Testa nível de autonomia para empréstimo."""
    nivel = regras.nivel_autonomia("emprestimo")
    assert nivel == "PROPOE"


def test_nivel_autonomia_baixa(regras):
    """Testa nível de autonomia para baixa."""
    nivel = regras.nivel_autonomia("baixa")
    assert nivel == "ESCALA"


def test_nivel_autonomia_alocacao_com_estoque(regras):
    """Testa nível de autonomia para alocação com estoque."""
    nivel = regras.nivel_autonomia("alocacao", tem_estoque=True)
    assert nivel == "FAZ_SOZINHO"


def test_nivel_autonomia_alocacao_sem_estoque_valor_baixo(regras):
    """Testa nível de autonomia para alocação sem estoque, valor baixo."""
    nivel = regras.nivel_autonomia("alocacao", valor=400.0, tem_estoque=False)
    assert nivel == "FAZ_SOZINHO"


def test_nivel_autonomia_alocacao_sem_estoque_valor_alto(regras):
    """Testa nível de autonomia para alocação sem estoque, valor alto."""
    nivel = regras.nivel_autonomia("alocacao", valor=600.0, tem_estoque=False)
    assert nivel == "PROPOE"


def test_validar_devolucao_valida(regras):
    """Testa validação de devolução válida."""
    valido, msg = regras.validar_devolucao("PAT-001", "alocado")
    assert valido is True
    assert msg == ""


def test_validar_devolucao_invalida(regras):
    """Testa validação de devolução inválida."""
    valido, msg = regras.validar_devolucao("PAT-001", "disponivel")
    assert valido is False
    assert "não está alocado" in msg.lower()


def test_validar_baixa_valida(regras):
    """Testa validação de baixa válida."""
    valido, msg = regras.validar_baixa("PAT-001", "danificado")
    assert valido is True
    assert msg == ""


def test_validar_baixa_invalida(regras):
    """Testa validação de baixa inválida."""
    valido, msg = regras.validar_baixa("PAT-001", "disponivel")
    assert valido is False
    assert "não pode ser baixado" in msg.lower()


def test_calcular_dias_cobranca_nao_cobrar(regras):
    """Testa cálculo de cobrança - não cobrar."""
    resultado = regras.calcular_dias_cobranca(3)
    assert resultado == "nao_cobrar"


def test_calcular_dias_cobranca_cobrar(regras):
    """Testa cálculo de cobrança - cobrar."""
    resultado = regras.calcular_dias_cobranca(7)
    assert resultado == "cobrar"


def test_calcular_dias_cobranca_escalar(regras):
    """Testa cálculo de cobrança - escalar."""
    resultado = regras.calcular_dias_cobranca(12)
    assert resultado == "escalar"


def test_validar_emprestimo_valido(regras):
    """Testa validação de empréstimo válido."""
    valido, msg = regras.validar_emprestimo(5)
    assert valido is True
    assert msg == ""


def test_validar_emprestimo_invalido(regras):
    """Testa validação de empréstimo inválido."""
    valido, msg = regras.validar_emprestimo(10)
    assert valido is False
    assert "máximo" in msg.lower()


def test_bloquear_email_externo(regras):
    """Testa bloqueio de e-mail externo."""
    assert regras.bloquear_email_externo("email_externo") is True
    assert regras.bloquear_email_externo("cenario") is False
    assert regras.bloquear_email_externo("painel") is False
