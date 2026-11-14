"""
Nó 7: Executar — Executa ações aprovadas do plano.
"""

import logging
from typing import Any, Dict
from ..state import AgentState, AcaoFeita
from ..mcp_client import MCPClient
from ..llm import LLMClient

logger = logging.getLogger(__name__)


def _executar_acao(acao: Dict[str, Any], state: AgentState, 
                   mcp: MCPClient, llm: LLMClient) -> Any:
    """
    Executa uma ação específica.
    
    Args:
        acao: dicionário com tool, args, motivo, nivel
        state: estado atual
        mcp: cliente MCP
        llm: cliente LLM
    
    Returns:
        resultado da execução
    """
    tool = acao.get("tool", "")
    args = acao.get("args", {})
    
    logger.info(f"Executando: {tool}")
    
    # Responder evento
    if tool == "responder_evento":
        return mcp.responder_evento(args)
    
    # Registrar devolução
    elif tool == "registrar_devolucao":
        return mcp.registrar_devolucao(args)
    
    # Alocar item
    elif tool == "alocar_item":
        return mcp.alocar_item(args)
    
    # Reservar kit
    elif tool == "reservar_kit":
        return mcp.reservar_kit(args)
    
    # Trocar item defeito
    elif tool == "trocar_item_defeito":
        return mcp.trocar_item_defeito(args)
    
    # Propor empréstimo
    elif tool == "propor_emprestimo":
        return mcp.propor_emprestimo(args)
    
    # Registrar entrada
    elif tool == "registrar_entrada":
        return mcp.registrar_entrada(args)
    
    # Registrar saída
    elif tool == "registrar_saida":
        return mcp.registrar_saida(args)
    
    # Baixar item
    elif tool == "baixar_item":
        return mcp.baixar_item(args)
    
    # Registrar entrega de compra
    elif tool == "registrar_entrega_compra":
        return mcp.registrar_entrega_compra(args)
    
    else:
        raise ValueError(f"Tool desconhecida: {tool}")


def node(state: AgentState, mcp: MCPClient, llm: LLMClient) -> AgentState:
    """
    Executa ações aprovadas do plano.
    
    Se não aprovado, retorna sem executar.
    Registra cada ação executada.
    """
    if not state.get("aprovado"):
        logger.info(f"Plano não aprovado, pulando execução")
        return state
    
    logger.info(f"Executando plano para evento {state['evento_id']}...")
    
    acoes_feitas: list[AcaoFeita] = []
    
    try:
        for acao in state.get("plano", []):
            try:
                resultado = _executar_acao(acao, state, mcp, llm)
                acoes_feitas.append({
                    "tool": acao.get("tool", ""),
                    "args": acao.get("args", {}),
                    "resultado": resultado
                })
                logger.info(f"Ação executada: {acao.get('tool')}")
            except Exception as e:
                logger.error(f"Erro ao executar {acao.get('tool')}: {e}")
                state["erros"].append(f"executar {acao.get('tool')}: {str(e)}")
        
        state["acoes_feitas"] = acoes_feitas
        logger.info(f"Execução concluída: {len(acoes_feitas)} ações")
        return state
    
    except Exception as e:
        logger.error(f"Erro ao executar plano: {e}")
        state["erros"].append(f"executar: {str(e)}")
        return state
