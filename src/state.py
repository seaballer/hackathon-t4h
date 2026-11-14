"""
Definição do estado compartilhado entre agentes (TypedDict).
"""

from typing import TypedDict, Optional, Any, List, Dict
from datetime import datetime


class PlanoAcao(TypedDict, total=False):
    """Ação planejada pelo Analista."""
    tool: str
    args: Dict[str, Any]
    motivo: str
    nivel: str  # FAZ_SOZINHO | PROPOE | ESCALA


class AcaoFeita(TypedDict, total=False):
    """Ação executada pelo Executor."""
    tool: str
    args: Dict[str, Any]
    resultado: Any
    tokens: int
    timestamp: str


class AgentState(TypedDict, total=False):
    """
    Estado compartilhado entre agentes.
    Checkpoint: SqliteSaver com thread_id = evento_id.
    """

    # ===== Evento atual =====
    evento_id: str
    evento: Dict[str, Any]  # payload do proximo_evento
    origem: str  # "cenario" | "painel" | "mundo"

    # ===== Resultado do Analista =====
    tipo: str  # enum de 12 tipos
    # patrimonio, colaborador_id, data, itens[], confianca
    entidades: Dict[str, Any]
    plano: List[PlanoAcao]  # [{tool, args, motivo, nivel}]

    # ===== Resultado do Revisor =====
    plano_aprovado: List[PlanoAcao]
    nivel_final: str  # FAZ_SOZINHO | PROPOE | ESCALA
    bloqueios: List[str]  # razões de bloqueio

    # ===== Execução =====
    acoes_feitas: List[AcaoFeita]  # {tool, args, resultado, tokens}
    resposta_remetente: str

    # ===== Contexto compartilhado (injetado pelo Coordenador) =====
    data_simulada: str  # AAAA-MM-DD
    cache: Dict[str, Any]  # regras, catalogo, colaboradores (estáticos)
    pendencias: Dict[str, Any]  # devolucoes, compras_em_transito, aprovacoes

    # ===== Metadados =====
    encerrado: bool
    erros: List[str]
