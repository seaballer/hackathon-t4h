"""
Nó 7: Executar — Executa ações aprovadas do plano.
"""

import logging
from typing import Any, Dict
from ..state import AgentState, AcaoFeita
from ..mcp_client import MCPClient
from ..llm import LLMClient

logger = logging.getLogger(__name__)


def _normalizar_itens_kit(itens: Any) -> list[Dict[str, str]]:
    if not isinstance(itens, list) or not itens:
        raise ValueError("A reserva do kit exige uma lista de itens.")

    solicitados: list[Dict[str, str]] = []
    for item in itens:
        if isinstance(item, str) and item.strip():
            solicitados.append({"tipo": item.strip()})
            continue
        if not isinstance(item, dict):
            raise ValueError("Cada item do kit deve informar tipo ou patrimonio.")

        patrimonio = item.get("patrimonio")
        tipo = item.get("tipo")
        if patrimonio:
            solicitados.append({"patrimonio": str(patrimonio)})
        elif tipo:
            quantidade = item.get("quantidade", 1)
            if type(quantidade) is not int or quantidade < 1:
                raise ValueError("quantidade do item deve ser um inteiro positivo.")
            solicitados.extend({"tipo": str(tipo)} for _ in range(quantidade))
        else:
            raise ValueError("Cada item do kit deve informar tipo ou patrimonio.")
    return solicitados


def _kit_padrao(
    state: AgentState,
    mcp: MCPClient,
    colaborador_id: str,
) -> list[str]:
    colaborador = mcp.consultar_colaborador(
        {"colaborador_id": colaborador_id}
    ).get("colaborador")
    if not colaborador:
        raise ValueError(f"Colaborador {colaborador_id!r} não encontrado.")

    cached = state.get("cache", {}).get("regras")
    if isinstance(cached, dict) and isinstance(cached.get("registros"), list):
        registros = cached["registros"]
    elif isinstance(cached, list):
        registros = cached
    else:
        registros = mcp.consultar("regras", limite=100).get("registros", [])

    regras = {
        registro["regra"]: registro.get("valor")
        for registro in registros
        if isinstance(registro, dict) and registro.get("regra")
    }
    kit = regras.get("kit_padrao")
    if not isinstance(kit, list) or not kit:
        raise ValueError("A base regras não contém um kit_padrao válido.")

    extras_por_area = regras.get("kit_extra_por_area", {})
    area = colaborador.get("area", "")
    extras = extras_por_area.get(area, []) if isinstance(extras_por_area, dict) else []
    return [*kit, *extras]


def _reservar_kit(
    args: Dict[str, Any],
    state: AgentState,
    mcp: MCPClient,
) -> Dict[str, Any]:
    colaborador_id = args.get("colaborador_id") or state.get(
        "entidades", {}
    ).get("colaborador_id")
    if not colaborador_id:
        raise ValueError("reservar_kit exige colaborador_id.")

    itens = args.get("itens")
    if not itens:
        itens = _kit_padrao(state, mcp, colaborador_id)
    solicitados = _normalizar_itens_kit(itens)

    selecionados: list[Dict[str, Any]] = []
    patrimonios: set[str] = set()
    for solicitado in solicitados:
        filtro = (
            {"patrimonio": solicitado["patrimonio"]}
            if "patrimonio" in solicitado
            else {"tipo": solicitado["tipo"], "status": "disponível"}
        )
        encontrados = mcp.consultar_inventario(filtro).get("itens", [])
        candidatos = [
            item
            for item in encontrados
            if item.get("status") in {"disponível", "disponivel"}
            and item.get("situacao") in {"novo", "usado"}
            and not item.get("com_quem")
            and item.get("patrimonio") not in patrimonios
        ]
        if not candidatos:
            identificador = solicitado.get("patrimonio", solicitado.get("tipo"))
            raise ValueError(
                f"Não há item disponível e utilizável para {identificador!r}."
            )
        escolhido = sorted(candidatos, key=lambda item: item["patrimonio"])[0]
        patrimonios.add(escolhido["patrimonio"])
        selecionados.append(escolhido)

    evento_id = args.get("evento_id") or state.get("evento_id")
    atualizados: list[Dict[str, Any]] = []
    try:
        for item in selecionados:
            resultado = mcp.atualizar(
                "inventario",
                item["patrimonio"],
                {"status": "reservado", "com_quem": colaborador_id},
                evento_id=evento_id,
            )
            atualizados.append({
                "patrimonio": item["patrimonio"],
                "resultado": resultado,
            })
    except Exception as exc:
        erros_rollback = []
        for item in reversed(selecionados[:len(atualizados)]):
            try:
                mcp.atualizar(
                    "inventario",
                    item["patrimonio"],
                    {"status": "disponível", "com_quem": ""},
                    evento_id=evento_id,
                )
            except Exception as rollback_exc:
                erros_rollback.append(
                    f"{item['patrimonio']}: {rollback_exc}"
                )
        if erros_rollback:
            raise RuntimeError(
                f"Falha ao reservar kit ({exc}); rollback incompleto: "
                + "; ".join(erros_rollback)
            ) from exc
        raise

    return {"itens_reservados": atualizados}


def _registrar_entrega_compra(
    args: Dict[str, Any],
    state: AgentState,
    mcp: MCPClient,
) -> Dict[str, Any]:
    itens = args.get("itens") or args.get("patrimonios") or []
    if not isinstance(itens, list) or not itens:
        raise ValueError(
            "registrar_entrega_compra exige os patrimônios já cadastrados "
            "no inventário; o MCP não permite registrar novos itens."
        )

    patrimonios = []
    for item in itens:
        patrimonio = item.get("patrimonio") if isinstance(item, dict) else item
        if not isinstance(patrimonio, str) or not patrimonio.strip():
            raise ValueError("Cada item entregue deve informar patrimonio.")
        if patrimonio in patrimonios:
            raise ValueError(f"Patrimônio duplicado na entrega: {patrimonio}.")
        patrimonios.append(patrimonio)

    inventario = []
    for patrimonio in patrimonios:
        itens_encontrados = mcp.consultar_inventario(
            {"patrimonio": patrimonio}
        ).get("itens", [])
        if not itens_encontrados:
            raise ValueError(
                f"Patrimônio {patrimonio!r} não está cadastrado no inventário."
            )
        item = itens_encontrados[0]
        if item.get("status") not in {"em_transito", "em trânsito"}:
            raise ValueError(
                f"Patrimônio {patrimonio!r} não está em trânsito "
                f"(status atual: {item.get('status')!r})."
            )
        inventario.append(item)

    evento_id = args.get("evento_id") or state.get("evento_id")
    atualizados = [
        mcp.atualizar(
            "inventario",
            item["patrimonio"],
            {
                "status": "disponível",
                "situacao": "novo",
                "com_quem": "",
            },
            evento_id=evento_id,
        )
        for item in inventario
    ]
    return {"itens_recebidos": atualizados}


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
    
    # A resposta é enviada no nó final, depois que as ações terminam.
    if tool == "responder_evento":
        return {"status": "resposta_pendente"}
    
    if tool in {"reservar_kit", "registrar_entrada"}:
        return _reservar_kit(args, state, mcp)

    if tool == "registrar_entrega_compra":
        return _registrar_entrega_compra(args, state, mcp)

    if tool == "propor_emprestimo":
        raise ValueError(
            "propor_emprestimo requer aprovação humana; a fila de aprovação "
            "ainda não está implementada."
        )

    if tool in {"registrar_devolucao", "alocar_item", "trocar_item_defeito", "baixar_item"}:
        patrimonio = args.get("patrimonio")
        if not patrimonio:
            raise ValueError(f"{tool} exige patrimonio.")

        updates = {
            "registrar_devolucao": {
                "status": "disponível",
                "situacao": "usado",
                "com_quem": "",
            },
            "alocar_item": {"status": "alocado", "situacao": "usado"},
            "trocar_item_defeito": {"status": "defeituoso"},
            "baixar_item": {"status": "baixado"},
        }[tool]
        if tool == "alocar_item":
            colaborador_id = args.get("colaborador_id") or state.get(
                "entidades", {}
            ).get("colaborador_id")
            if not colaborador_id:
                raise ValueError("alocar_item exige colaborador_id.")
            updates["com_quem"] = colaborador_id

        return mcp.atualizar(
            "inventario",
            patrimonio,
            updates,
            evento_id=args.get("evento_id") or state.get("evento_id"),
        )

    if tool == "registrar_saida":
        colaborador_id = args.get("colaborador_id") or state.get(
            "entidades", {}
        ).get("colaborador_id")
        if not colaborador_id:
            raise ValueError("registrar_saida exige colaborador_id.")
        resultado = mcp.consultar_inventario({"com_quem": colaborador_id})
        atualizados = []
        for item in resultado.get("itens", []):
            atualizados.append(
                mcp.atualizar(
                    "inventario",
                    item["patrimonio"],
                    {"status": "disponível", "com_quem": ""},
                    evento_id=args.get("evento_id") or state.get("evento_id"),
                )
            )
        return {"atualizados": atualizados}
    
    else:
        raise ValueError(
            f"Ação {tool!r} ainda não tem operação equivalente no servidor MCP."
        )


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
