"""
Regras de negócio para gestão de equipamentos.
Puro Python, testável, sem dependências externas.
"""

from typing import Dict, List, Any, Tuple
from datetime import datetime


class RegrasEquipamentos:
    """Validação e aplicação de regras de negócio."""

    # Limites de autonomia
    LIMITE_COMPRA_AUTONOMA = 500.0  # R$
    DIAS_COBRANCA_DEVOLUCAO = 5  # dias úteis
    DIAS_ESCALA_DEVOLUCAO = 10  # dias úteis
    DIAS_EMPRESTIMO = 7  # dias úteis
    ESTOQUE_MINIMO = 3  # itens

    # Tipos de eventos
    TIPOS_EVENTO = {
        "duvida",
        "consulta_estoque",
        "devolucao",
        "resposta_cobranca",
        "alocacao",
        "reserva_kit",
        "troca_defeito",
        "emprestimo",
        "entrada_pessoa",
        "saida_pessoa",
        "baixa",
        "entrega_compra",
        "outro"
    }

    # Status de inventário
    STATUS_INVENTARIO = {
        "disponivel",
        "reservado",
        "alocado",
        "danificado",
        "quebrado",
        "perdido",
        "em_transito"
    }

    def __init__(self, cache: Dict[str, Any]):
        """
        Args:
            cache: dicionário com regras, catalogo, colaboradores (estáticos)
        """
        self.cache = cache

    def validar_tipo_evento(self, tipo: str) -> Tuple[bool, str]:
        """Valida se o tipo de evento é conhecido."""
        if tipo in self.TIPOS_EVENTO:
            return True, ""
        return False, f"Tipo desconhecido: {tipo}"

    def validar_status_inventario(self, status: str) -> Tuple[bool, str]:
        """Valida se o status de inventário é válido."""
        if status in self.STATUS_INVENTARIO:
            return True, ""
        return False, f"Status inválido: {status}"

    def pode_comprar_autonomamente(self, valor: float) -> bool:
        """Retorna True se o valor está dentro do limite de autonomia."""
        return valor <= self.LIMITE_COMPRA_AUTONOMA

    def nivel_autonomia(self, tipo: str, valor: float = 0.0,
                        tem_estoque: bool = True) -> str:
        """
        Determina o nível de autonomia para uma ação.

        Returns:
            "FAZ_SOZINHO" | "PROPOE" | "ESCALA"
        """
        if tipo in ["duvida", "consulta_estoque", "devolucao", "resposta_cobranca"]:
            return "FAZ_SOZINHO"

        if tipo in ["alocacao", "reserva_kit"]:
            if not tem_estoque:
                if self.pode_comprar_autonomamente(valor):
                    return "FAZ_SOZINHO"
                else:
                    return "PROPOE"
            return "FAZ_SOZINHO"

        if tipo in ["troca_defeito", "entrega_compra"]:
            return "FAZ_SOZINHO"

        if tipo in ["emprestimo"]:
            return "PROPOE"

        if tipo in ["entrada_pessoa", "saida_pessoa"]:
            if not tem_estoque:
                if self.pode_comprar_autonomamente(valor):
                    return "FAZ_SOZINHO"
                else:
                    return "PROPOE"
            return "FAZ_SOZINHO"

        if tipo in ["baixa"]:
            return "ESCALA"

        return "ESCALA"  # padrão para "outro" ou desconhecido

    def validar_devolucao(self, patrimonio: str, status_atual: str) -> Tuple[bool, str]:
        """Valida se um item pode ser devolvido."""
        if status_atual not in ["alocado", "reservado"]:
            return False, f"Item não está alocado/reservado (status: {status_atual})"
        return True, ""

    def validar_baixa(self, patrimonio: str, status_atual: str) -> Tuple[bool, str]:
        """Valida se um item pode ser baixado."""
        if status_atual not in ["danificado", "quebrado", "perdido"]:
            return False, f"Item não pode ser baixado (status: {status_atual})"
        return True, ""

    def calcular_dias_cobranca(self, dias_uteis: int) -> str:
        """
        Determina se deve cobrar devolução.

        Returns:
            "nao_cobrar" | "cobrar" | "escalar"
        """
        if dias_uteis < self.DIAS_COBRANCA_DEVOLUCAO:
            return "nao_cobrar"
        elif dias_uteis < self.DIAS_ESCALA_DEVOLUCAO:
            return "cobrar"
        else:
            return "escalar"

    def validar_emprestimo(self, dias_emprestimo: int) -> Tuple[bool, str]:
        """Valida se o período de empréstimo é aceitável."""
        if dias_emprestimo > self.DIAS_EMPRESTIMO:
            return False, f"Empréstimo máximo é {self.DIAS_EMPRESTIMO} dias úteis"
        return True, ""

    def detectar_duplicidade(self, evento_id: str, eventos_recentes: List[Dict]) -> bool:
        """Detecta se há evento duplicado recentemente."""
        for evt in eventos_recentes:
            if evt.get("evento_id") == evento_id:
                return True
        return False

    def bloquear_email_externo(self, origem: str) -> bool:
        """Bloqueia eventos de e-mail externo (segurança)."""
        return origem == "email_externo"
