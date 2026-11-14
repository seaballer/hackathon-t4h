"""
Nó 3: Resolver Dados — Resolve entidades consultando MCP.
"""

import logging
from ..state import AgentState
from ..mcp_client import MCPClient

logger = logging.getLogger(__name__)


def node(state: AgentState, mcp: MCPClient) -> AgentState:
    """
    Resolve entidades consultando MCP.
    
    Consulta inventário, colaboradores, etc.
    """
    entidades = state.get("entidades", {})
    
    if not entidades:
        logger.debug("Nenhuma entidade para resolver")
        return state
    
    logger.info(f"Resolvendo entidades para evento {state['evento_id']}...")
    
    try:
        # Resolver patrimônio
        if entidades.get("patrimonio"):
            try:
                inv = mcp.consultar_inventario({
                    "patrimonio": entidades["patrimonio"]
                })
                if inv.get("itens"):
                    entidades["item_atual"] = inv["itens"][0]
                    logger.info(f"Patrimônio resolvido: {entidades['patrimonio']}")
            except Exception as e:
                logger.warning(f"Erro ao consultar inventário: {e}")
        
        # Resolver colaborador
        if entidades.get("colaborador_id"):
            try:
                colab = mcp.consultar_colaborador({
                    "colaborador_id": entidades["colaborador_id"]
                })
                if colab.get("colaborador"):
                    entidades["colaborador_info"] = colab["colaborador"]
                    logger.info(f"Colaborador resolvido: {entidades['colaborador_id']}")
            except Exception as e:
                logger.warning(f"Erro ao consultar colaborador: {e}")
        
        state["entidades"] = entidades
        return state
    
    except Exception as e:
        logger.error(f"Erro ao resolver dados: {e}")
        state["erros"].append(f"resolver_dados: {str(e)}")
        return state
