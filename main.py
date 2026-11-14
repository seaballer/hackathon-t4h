"""
Ponto de entrada: executa o time de agentes.
"""

from src.state import AgentState
from src.graph import criar_grafo
from src.rules import RegrasEquipamentos
from src.clock import Clock
from src.llm import LLMClient
from src.mcp_client import MCPClient
import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("agentes.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Função principal."""

    # Carregar variáveis de ambiente
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    logger.info(f"Carregando .env de: {env_path}")
    load_dotenv(env_path)

    # Verificar se OPENAI_API_KEY foi carregado
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        logger.info(f"[OK] OPENAI_API_KEY carregado: {api_key[:10]}...")
    else:
        logger.warning(
            "[WARN] OPENAI_API_KEY não encontrado - usando modo offline")

    # Argumentos
    parser = argparse.ArgumentParser(
        description="Time de agentes - Gestão de Equipamentos")
    parser.add_argument("--mcp-url", default="http://localhost:8765/mcp",
                        help="URL do servidor MCP")
    parser.add_argument("--max-eventos", type=int, default=None,
                        help="Máximo de eventos a processar (padrão: sem limite)")
    parser.add_argument("--checkpoint-dir", default=".checkpoints",
                        help="Diretório para checkpoints")

    args = parser.parse_args()

    logger.info("=== Iniciando Time de Agentes ===")
    logger.info(f"MCP URL: {args.mcp_url}")

    mcp = None
    try:
        # Inicializar componentes
        mcp = MCPClient(base_url=args.mcp_url)
        mcp.initialize(agente="orquestrador")
        llm = LLMClient()
        clock = Clock()
        regras = RegrasEquipamentos({})

        # Criar grafo
        graph = criar_grafo(mcp, llm, clock, regras, args.checkpoint_dir)

        # Estado inicial
        initial_state: AgentState = {
            "evento_id": "",
            "evento": None,
            "origem": "",
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

        # Executar grafo em laço
        eventos_processados = 0
        config = {"configurable": {"thread_id": "main"}}

        logger.info("Iniciando laço de processamento...")

        while True:
            # Executar um passo do grafo
            try:
                # Usar stream para processar um evento por vez
                for output in graph.stream(initial_state, config):
                    # output é um dict {node_name: state}
                    node_name = list(output.keys())[0]
                    state = output[node_name]

                    logger.info(f"Nó executado: {node_name}")

                    # Atualizar estado
                    initial_state = state

                    # Verificar encerramento
                    if state.get("encerrado"):
                        logger.info("Cenário encerrado")
                        break

                    # Verificar limite de eventos
                    if state.get("evento_id"):
                        eventos_processados += 1
                        if args.max_eventos and eventos_processados >= args.max_eventos:
                            logger.info(
                                f"Limite de eventos atingido: {eventos_processados}")
                            break

                # Verificar encerramento
                if initial_state.get("encerrado"):
                    break

                # Verificar limite
                if args.max_eventos and eventos_processados >= args.max_eventos:
                    break

            except KeyboardInterrupt:
                logger.info("Interrupção do usuário")
                break

            except Exception as e:
                logger.error(f"Erro no laço principal: {e}", exc_info=True)
                break

        # Relatório final
        logger.info("=== Relatório Final ===")
        logger.info(f"Eventos processados: {eventos_processados}")
        logger.info(f"Tokens LLM usados: {llm.obter_tokens_usados()}")
        logger.info(f"Erros: {len(initial_state.get('erros', []))}")

        if initial_state.get("erros"):
            logger.warning("Erros encontrados:")
            for erro in initial_state["erros"]:
                logger.warning(f"  - {erro}")

        logger.info("=== Execução Finalizada ===")

    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if mcp is not None:
            mcp.close()


if __name__ == "__main__":
    main()
