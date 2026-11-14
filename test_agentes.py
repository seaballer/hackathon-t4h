"""
Teste para executar os agentes com eventos simulados.
"""

from src.rules import RegrasEquipamentos
from src.clock import Clock
from src.mcp_client import MCPClient
from src.llm import LLMClient
from src.graph import criar_grafo
from src.state import AgentState
import os
import sys
import logging
from dotenv import load_dotenv

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_coordenador_com_evento():
    """Testa o agente coordenador com um evento simulado."""

    # Carregar variáveis de ambiente
    load_dotenv()

    logger.info("=== Teste do Agente Coordenador ===")

    # Tentar ler porta do arquivo .mcp_port
    mcp_url = "http://localhost:8766/mcp"
    if os.path.exists(".mcp_port"):
        try:
            with open(".mcp_port", "r") as f:
                porta = f.read().strip()
                mcp_url = f"http://localhost:{porta}/mcp"
                logger.info(f"Porta MCP lida do arquivo: {porta}")
        except Exception as e:
            logger.warning(f"Erro ao ler porta MCP: {e}, usando padrão")

    # Inicializar componentes
    mcp = MCPClient(base_url=mcp_url)
    llm = LLMClient()
    clock = Clock()
    regras = RegrasEquipamentos({})

    # Criar grafo
    graph = criar_grafo(mcp, llm, clock, regras)

    # Estado inicial com um evento simulado
    initial_state: AgentState = {
        "evento_id": "test_001",
        "evento": {
            "id": "test_001",
            "tipo": "consulta_estoque",
            "origem": "teste",
            "dados": {
                "patrimonio": "PAT-001",
                "colaborador_id": "COL-001"
            }
        },
        "origem": "teste",
        "tipo": "",
        "entidades": {},
        "plano": [],
        "plano_aprovado": [],
        "nivel_final": "",
        "bloqueios": [],
        "acoes_feitas": [],
        "resposta_remetente": "",
        "data_simulada": "",
        "cache": {},
        "pendencias": {},
        "encerrado": False,
        "erros": []
    }

    config = {"configurable": {"thread_id": "test"}}

    logger.info("Executando grafo com evento simulado...")

    # Executar o grafo
    for output in graph.stream(initial_state, config):
        node_name = list(output.keys())[0]
        state = output[node_name]

        logger.info(f"Nó executado: {node_name}")
        logger.info(f"  - Tipo: {state.get('tipo')}")
        logger.info(f"  - Entidades: {state.get('entidades')}")
        logger.info(f"  - Plano: {state.get('plano')}")

        initial_state = state

        if state.get("encerrado"):
            logger.info("Cenário encerrado")
            break

    # Relatório final
    logger.info("=== Relatório Final ===")
    logger.info(f"Evento ID: {initial_state.get('evento_id')}")
    logger.info(f"Tipo: {initial_state.get('tipo')}")
    logger.info(f"Entidades: {initial_state.get('entidades')}")
    logger.info(f"Plano: {initial_state.get('plano')}")
    logger.info(f"Erros: {len(initial_state.get('erros', []))}")

    if initial_state.get("erros"):
        logger.warning("Erros encontrados:")
        for erro in initial_state["erros"]:
            logger.warning(f"  - {erro}")

    logger.info("=== Teste Concluído ===")


if __name__ == "__main__":
    test_coordenador_com_evento()
