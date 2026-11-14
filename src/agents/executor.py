"""
Agente Executor: executa ações, atualiza inventário, responde eventos, envia mensagens.
"""

import logging
from typing import Dict, Any
from ..state import AgentState, AcaoFeita
from ..mcp_client import MCPClient
from ..llm import LLMClient

logger = logging.getLogger(__name__)


def executor(state: AgentState, mcp: MCPClient, llm: LLMClient) -> AgentState:
    """
    Executor: executa o plano aprovado.

    Responsabilidades:
    - Executar cada ação do plano
    - Registrar resultado
    - Tratar erros e retry
    - Manter idempotência
    """

    if not state.get("plano_aprovado"):
        logger.warning("Executor: sem plano aprovado para executar")
        state["acoes_feitas"] = []
        return state

    logger.info(f"Executor processando {len(state['plano_aprovado'])} ações")

    acoes_feitas: list[AcaoFeita] = []

    try:
        for acao in state["plano_aprovado"]:
            logger.info(f"Executando: {acao['tool']}")

            try:
                resultado = _executar_acao(acao, state, mcp, llm)

                acao_feita: AcaoFeita = {
                    "tool": acao["tool"],
                    "args": acao["args"],
                    "resultado": resultado,
                    "tokens": llm.obter_tokens_usados() if llm else 0
                }
                acoes_feitas.append(acao_feita)

                logger.info(f"Ação {acao['tool']} executada com sucesso")

            except Exception as e:
                logger.error(f"Erro ao executar {acao['tool']}: {e}")
                state["erros"].append(f"{acao['tool']}: {str(e)}")

                # Continuar com próximas ações
                continue

        state["acoes_feitas"] = acoes_feitas

        # Gerar resposta ao remetente se houver
        if state.get("tipo") and state.get("entidades"):
            try:
                resposta = llm.redigir_resposta(
                    state["tipo"],
                    state["entidades"],
                    {"acoes": len(acoes_feitas)}
                )
                state["resposta_remetente"] = resposta
            except Exception as e:
                logger.warning(f"Erro ao redigir resposta: {e}")
                state["resposta_remetente"] = "Sua solicitação foi processada."

        logger.info(
            f"Executor finalizou: {len(acoes_feitas)} ações executadas")

        return state

    except Exception as e:
        logger.error(f"Erro no Executor: {e}")
        state["erros"].append(str(e))
        state["acoes_feitas"] = acoes_feitas
        return state


def _executar_acao(acao: Dict[str, Any], state: AgentState,
                   mcp: MCPClient, llm: LLMClient) -> Any:
    """Executa uma ação individual."""

    tool = acao["tool"]
    args = acao["args"]

    if tool == "responder_evento":
        evento_id = args.get("evento_id")

        # Gerar resposta se não houver
        resposta = args.get("resposta", "")
        if not resposta and llm:
            resposta = llm.redigir_resposta(
                state.get("tipo", ""),
                state.get("entidades", {}),
                {}
            )

        return mcp.responder_evento(evento_id, resposta)

    elif tool == "enviar_mensagem":
        destinatario = args.get("destinatario")
        assunto = args.get("assunto", "Notificação")
        corpo = args.get("corpo", "")
        evento_id = args.get("evento_id")

        if not corpo and llm:
            corpo = llm.redigir_resposta(
                state.get("tipo", ""),
                state.get("entidades", {}),
                {"assunto": assunto}
            )

        return mcp.enviar_mensagem(destinatario, assunto, corpo, evento_id)

    elif tool == "atualizar_inventario":
        patrimonio = args.get("patrimonio")
        atualizacoes = {
            "status": args.get("status"),
            "observacao": args.get("observacao", "")
        }

        return mcp.atualizar_inventario(patrimonio, atualizacoes)

    elif tool == "consultar_inventario":
        filtros = args.get("filtros", {})
        return mcp.consultar_inventario(filtros)

    elif tool == "registrar":
        base = args.get("base")
        dados = args.get("dados", {})

        return mcp.registrar(base, dados)

    elif tool == "atualizar":
        base = args.get("base")
        id_registro = args.get("id")
        atualizacoes = args.get("atualizacoes", {})

        return mcp.atualizar(base, id_registro, atualizacoes)

    else:
        raise ValueError(f"Tool desconhecida: {tool}")
