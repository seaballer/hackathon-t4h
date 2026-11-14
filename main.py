"""
Ponto de entrada: executa o time de agentes.
"""

# autopep8: off
# isort: off
# fmt: off
# ATENCAO: nao mova os imports abaixo para cima da verificacao do venv.
# Os formatadores estao desligados neste trecho de proposito.
import atexit
import os
import subprocess
import sys
import time
import urllib.request

# Garante que o script rode com o Python do venv do projeto (onde estao as
# dependencias). Se for iniciado por outro interpretador (ex.: .venv ou o
# Python global), reinicia automaticamente usando venv\Scripts\python.exe.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_VENV_PYTHON = os.path.join(
    _BASE_DIR, "venv", "Scripts" if os.name == "nt" else "bin",
    "python.exe" if os.name == "nt" else "python",
)
if (
    os.path.exists(_VENV_PYTHON)
    and os.path.normcase(os.path.abspath(sys.prefix))
    != os.path.normcase(os.path.join(_BASE_DIR, "venv"))
):
    sys.exit(subprocess.call(
        [_VENV_PYTHON, os.path.abspath(__file__), *sys.argv[1:]]))

import argparse
import logging
from dotenv import load_dotenv
from src.mcp_client import MCPClient
from src.llm import LLMClient
from src.clock import Clock
from src.rules import RegrasEquipamentos
from src.graph import criar_grafo
from src.state import AgentState
# fmt: on
# isort: on
# autopep8: on


# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_BASE_DIR, "agentes.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

_PORT_FILE = os.path.join(_BASE_DIR, ".mcp_port")


def _servidor_ativo(porta: str) -> bool:
    """Retorna True se o servidor MCP local responde em /health."""
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{porta}/health", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _ler_porta() -> str | None:
    try:
        with open(_PORT_FILE, "r") as f:
            return f.read().strip() or None
    except OSError:
        return None


def garantir_servidor_mcp(timeout: float = 20.0) -> str:
    """
    Conecta ao servidor MCP local que deve estar rodando via iniciar.ps1.
    Aguarda até 'timeout' segundos pela porta estar disponível.
    Retorna a URL base do MCP.
    """
    limite = time.time() + timeout
    while time.time() < limite:
        porta = _ler_porta()
        if porta and _servidor_ativo(porta):
            logger.info(f"Servidor MCP conectado na porta {porta}")
            return f"http://127.0.0.1:{porta}/mcp"
        time.sleep(0.5)

    raise RuntimeError(
        f"Servidor MCP não encontrado em {timeout:.0f}s. "
        f"Execute: .\\iniciar.ps1")


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
    parser.add_argument("--mcp-url", default=None,
                        help="URL do servidor MCP (padrão: inicia/usa o "
                             "servidor local src/mcp_server.py)")
    parser.add_argument("--max-eventos", type=int, default=None,
                        help="Máximo de eventos a processar (padrão: sem limite)")
    parser.add_argument("--checkpoint-dir", default=".checkpoints",
                        help="Diretório para checkpoints")

    args = parser.parse_args()

    if args.mcp_url is None:
        try:
            args.mcp_url = garantir_servidor_mcp()
        except RuntimeError as e:
            logger.error(str(e))
            sys.exit(1)

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
        eventos_vistos: set = set()
        config = {"configurable": {"thread_id": "main"}}

        logger.info("Iniciando laço de processamento...")

        # Executar o grafo uma única vez
        try:
            # Usar stream para processar eventos
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

                # Contar eventos distintos (cada evento passa por vários nós)
                if node_name == "coordenador" and state.get("evento"):
                    eventos_vistos.add(state.get("evento_id"))
                    eventos_processados = len(eventos_vistos)

                # Parar só quando o evento atual terminou (o próximo nó seria
                # o coordenador, que já tiraria outro evento da fila)
                evento_terminou = node_name == "executor" or (
                    node_name == "revisor" and not state.get("plano_aprovado"))
                if (args.max_eventos and evento_terminou
                        and eventos_processados >= args.max_eventos):
                    logger.info(
                        f"Limite de eventos atingido: {eventos_processados}")
                    break

        except KeyboardInterrupt:
            logger.info("Interrupção do usuário")

        except Exception as e:
            logger.error(f"Erro no laço principal: {e}", exc_info=True)

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
