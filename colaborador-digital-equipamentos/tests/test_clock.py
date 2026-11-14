"""
Testes para o módulo de relógio.
"""

import pytest
from datetime import datetime, timedelta
from src.clock import Clock


@pytest.fixture
def clock():
    """Fixture com instância de Clock."""
    return Clock("2026-01-05")  # segunda-feira


def test_eh_dia_util_segunda(clock):
    """Testa se segunda é dia útil."""
    data = datetime(2026, 1, 5)  # segunda
    assert clock.eh_dia_util(data) is True


def test_eh_dia_util_sexta(clock):
    """Testa se sexta é dia útil."""
    data = datetime(2026, 1, 9)  # sexta
    assert clock.eh_dia_util(data) is True


def test_eh_dia_util_sabado(clock):
    """Testa se sábado não é dia útil."""
    data = datetime(2026, 1, 10)  # sábado
    assert clock.eh_dia_util(data) is False


def test_eh_dia_util_domingo(clock):
    """Testa se domingo não é dia útil."""
    data = datetime(2026, 1, 11)  # domingo
    assert clock.eh_dia_util(data) is False


def test_proximo_dia_util_segunda_para_terca(clock):
    """Testa próximo dia útil de segunda para terça."""
    data = datetime(2026, 1, 5)  # segunda
    proximo = clock.proximo_dia_util(data)
    assert proximo.weekday() == 1  # terça
    assert proximo.day == 6


def test_proximo_dia_util_sexta_para_segunda(clock):
    """Testa próximo dia útil de sexta para segunda."""
    data = datetime(2026, 1, 9)  # sexta
    proximo = clock.proximo_dia_util(data)
    assert proximo.weekday() == 0  # segunda
    assert proximo.day == 12


def test_dias_uteis_entre_mesmo_dia(clock):
    """Testa dias úteis entre o mesmo dia."""
    data = datetime(2026, 1, 5)  # segunda
    dias = clock.dias_uteis_entre(data, data)
    assert dias == 1


def test_dias_uteis_entre_segunda_a_sexta(clock):
    """Testa dias úteis de segunda a sexta."""
    data1 = datetime(2026, 1, 5)  # segunda
    data2 = datetime(2026, 1, 9)  # sexta
    dias = clock.dias_uteis_entre(data1, data2)
    assert dias == 5


def test_dias_uteis_entre_com_fim_de_semana(clock):
    """Testa dias úteis pulando fim de semana."""
    data1 = datetime(2026, 1, 9)  # sexta
    data2 = datetime(2026, 1, 12)  # segunda
    dias = clock.dias_uteis_entre(data1, data2)
    assert dias == 2  # sexta e segunda


def test_avancar_dia(clock):
    """Testa avanço de dia."""
    data_str = clock.avancar_dia()
    assert data_str == "2026-01-06"  # terça


def test_avancar_dia_pulando_fim_de_semana(clock):
    """Testa avanço de dia pulando fim de semana."""
    clock.data_atual = datetime(2026, 1, 9)  # sexta
    data_str = clock.avancar_dia()
    assert data_str == "2026-01-12"  # segunda


def test_data_str(clock):
    """Testa formato de data string."""
    data_str = clock.data_str()
    assert data_str == "2026-01-05"


def test_data_obj(clock):
    """Testa retorno de objeto datetime."""
    data_obj = clock.data_obj()
    assert isinstance(data_obj, datetime)
    assert data_obj.year == 2026
    assert data_obj.month == 1
    assert data_obj.day == 5
