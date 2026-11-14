"""
Nó 4: Montar Plano — Monta plano de ações baseado no tipo.
"""

import logging
from typing import List, Dict, Any
from ..state import AgentState, PlanoAcao
from ..rules import RegrasEquipamentos

logger = logging.getLogger(__name__)


def node(state: AgentState, regras: RegrasEquipamentos) -> AgentState:
    """
    Monta plano de ações baseado no tipo de evento.
    
    Cria lista de ações a executar.
    """
    tipo = state.get("tipo", "outro")
    entidades = state.get("entidades", {})
    evento_id = state.get("evento_id", "")
    
    logger.info(f"Montando plano para tipo: {tipo}")
    
    plano: List[PlanoAcao] = []
    
    try:
        # Dúvida: responder
        if tipo == "duvida":
            plano.append({
                "tool": "responder_evento",
                "args": {"evento_id": evento_id},
                "motivo": "Responder dúvida",
                "nivel": "FAZ_SOZINHO"
            })
        
        # Consulta de estoque: responder
        elif tipo == "consulta_estoque":
            plano.append({
                "tool": "responder_evento",
                "args": {"evento_id": evento_id},
                "motivo": "Responder consulta de estoque",
                "nivel": "FAZ_SOZINHO"
            })
        
        # Devolução: registrar devolução
        elif tipo == "devolucao":
            if entidades.get("patrimonio"):
                plano.append({
                    "tool": "registrar_devolucao",
                    "args": {
                        "evento_id": evento_id,
                        "patrimonio": entidades["patrimonio"]
                    },
                    "motivo": "Registrar devolução",
                    "nivel": "FAZ_SOZINHO"
                })
        
        # Resposta de cobrança: registrar
        elif tipo == "resposta_cobranca":
            plano.append({
                "tool": "responder_evento",
                "args": {"evento_id": evento_id},
                "motivo": "Registrar resposta de cobrança",
                "nivel": "FAZ_SOZINHO"
            })
        
        # Alocação: alocar item
        elif tipo == "alocacao":
            if entidades.get("patrimonio"):
                nivel = regras.nivel_autonomia(
                    tipo,
                    entidades.get("valor", 0.0),
                    bool(entidades.get("item_atual"))
                )
                plano.append({
                    "tool": "alocar_item",
                    "args": {
                        "evento_id": evento_id,
                        "patrimonio": entidades["patrimonio"]
                    },
                    "motivo": "Alocar item",
                    "nivel": nivel
                })
        
        # Reserva de kit: reservar
        elif tipo == "reserva_kit":
            nivel = regras.nivel_autonomia(
                tipo,
                entidades.get("valor", 0.0),
                bool(entidades.get("item_atual"))
            )
            plano.append({
                "tool": "reservar_kit",
                "args": {
                    "evento_id": evento_id,
                    "itens": entidades.get("itens", [])
                },
                "motivo": "Reservar kit",
                "nivel": nivel
            })
        
        # Troca de defeito: trocar
        elif tipo == "troca_defeito":
            if entidades.get("patrimonio"):
                plano.append({
                    "tool": "trocar_item_defeito",
                    "args": {
                        "evento_id": evento_id,
                        "patrimonio": entidades["patrimonio"]
                    },
                    "motivo": "Trocar item defeituoso",
                    "nivel": "FAZ_SOZINHO"
                })
        
        # Empréstimo: propor
        elif tipo == "emprestimo":
            if entidades.get("patrimonio"):
                plano.append({
                    "tool": "propor_emprestimo",
                    "args": {
                        "evento_id": evento_id,
                        "patrimonio": entidades["patrimonio"]
                    },
                    "motivo": "Propor empréstimo",
                    "nivel": "PROPOE"
                })
        
        # Entrada de pessoa: registrar
        elif tipo == "entrada_pessoa":
            plano.append({
                "tool": "registrar_entrada",
                "args": {
                    "evento_id": evento_id,
                    "colaborador_id": entidades.get("colaborador_id", "")
                },
                "motivo": "Registrar entrada de pessoa",
                "nivel": "FAZ_SOZINHO"
            })
        
        # Saída de pessoa: registrar
        elif tipo == "saida_pessoa":
            plano.append({
                "tool": "registrar_saida",
                "args": {
                    "evento_id": evento_id,
                    "colaborador_id": entidades.get("colaborador_id", "")
                },
                "motivo": "Registrar saída de pessoa",
                "nivel": "FAZ_SOZINHO"
            })
        
        # Baixa: baixar item
        elif tipo == "baixa":
            if entidades.get("patrimonio"):
                plano.append({
                    "tool": "baixar_item",
                    "args": {
                        "evento_id": evento_id,
                        "patrimonio": entidades["patrimonio"]
                    },
                    "motivo": "Baixar item",
                    "nivel": regras.nivel_autonomia(tipo)
                })
        
        # Entrega de compra: registrar
        elif tipo == "entrega_compra":
            plano.append({
                "tool": "registrar_entrega_compra",
                "args": {
                    "evento_id": evento_id,
                    "itens": entidades.get("itens", [])
                },
                "motivo": "Registrar entrega de compra",
                "nivel": "FAZ_SOZINHO"
            })
        
        # Outro: responder
        else:
            plano.append({
                "tool": "responder_evento",
                "args": {"evento_id": evento_id},
                "motivo": "Escalar evento desconhecido",
                "nivel": "ESCALA"
            })
        
        state["plano"] = plano
        logger.info(f"Plano montado com {len(plano)} ações")
        return state
    
    except Exception as e:
        logger.error(f"Erro ao montar plano: {e}")
        state["erros"].append(f"montar_plano: {str(e)}")
        return state
