"""
Gerenciamento de data simulada e dias úteis.
"""

from datetime import datetime, timedelta
from typing import Tuple


class Clock:
    """Relógio simulado para o expediente (08:00-18:00, dias úteis)."""

    def __init__(self, data_inicial: str = "2026-01-05"):
        """
        Args:
            data_inicial: data no formato AAAA-MM-DD
        """
        self.data_atual = datetime.strptime(data_inicial, "%Y-%m-%d")

    def eh_dia_util(self, data: datetime) -> bool:
        """Retorna True se é dia útil (seg-sex)."""
        return data.weekday() < 5  # 0-4 = seg-sex

    def proximo_dia_util(self, data: datetime) -> datetime:
        """Retorna o próximo dia útil."""
        data = data + timedelta(days=1)
        while not self.eh_dia_util(data):
            data = data + timedelta(days=1)
        return data

    def dias_uteis_entre(self, data1: datetime, data2: datetime) -> int:
        """Conta dias úteis entre duas datas (inclusive)."""
        if data1 > data2:
            data1, data2 = data2, data1

        count = 0
        current = data1
        while current <= data2:
            if self.eh_dia_util(current):
                count += 1
            current += timedelta(days=1)
        return count

    def avancar_dia(self) -> str:
        """Avança para o próximo dia útil e retorna a data em AAAA-MM-DD."""
        self.data_atual = self.proximo_dia_util(self.data_atual)
        return self.data_atual.strftime("%Y-%m-%d")

    def data_str(self) -> str:
        """Retorna a data atual em formato AAAA-MM-DD."""
        return self.data_atual.strftime("%Y-%m-%d")

    def data_obj(self) -> datetime:
        """Retorna o objeto datetime da data atual."""
        return self.data_atual
