import json

import httpx
import pytest

from src.mcp_client import MCPClient


def _sse(payload):
    return httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        text=f"event: message\ndata: {json.dumps(payload)}\n\n",
    )


def test_initialize_and_call_tool_uses_mcp_session():
    requests = []

    def handle(request):
        body = json.loads(request.content)
        requests.append((request, body))
        if body["method"] == "initialize":
            return httpx.Response(
                200,
                headers={
                    "content-type": "text/event-stream",
                    "mcp-session-id": "session-123",
                },
                text='event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{}}\n\n',
            )
        if body["method"] == "notifications/initialized":
            return httpx.Response(202)
        return _sse({
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {
                "content": [{
                    "type": "text",
                    "text": json.dumps({"status": "ok", "evento": None}),
                }],
                "isError": False,
            },
        })

    client = MCPClient(client=httpx.Client(transport=httpx.MockTransport(handle)))
    client.initialize(agente="teste")
    result = client.call_tool("proximo_evento", {"esperar_segundos": 0})

    assert result == {"status": "ok", "evento": None}
    assert requests[2][1]["params"] == {
        "name": "proximo_evento",
        "arguments": {"esperar_segundos": 0, "agente": "teste"},
    }
    assert requests[2][0].headers["mcp-session-id"] == "session-123"
    client.close()


def test_consultar_inventario_uses_real_mcp_tool_and_maps_records():
    def handle(request):
        body = json.loads(request.content)
        if body["method"] == "initialize":
            return httpx.Response(
                200,
                headers={
                    "content-type": "application/json",
                    "mcp-session-id": "session-123",
                },
                json={"jsonrpc": "2.0", "id": body["id"], "result": {}},
            )
        if body["method"] == "notifications/initialized":
            return httpx.Response(202)
        text = json.dumps({
            "status": "ok",
            "base": "inventario",
            "registros": [{"patrimonio": "EQ-1"}],
        })
        return _sse({
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {"content": [{"type": "text", "text": text}]},
        })

    client = MCPClient(client=httpx.Client(transport=httpx.MockTransport(handle)))
    result = client.consultar_inventario({"patrimonio": "EQ-1"})

    assert result["itens"] == [{"patrimonio": "EQ-1"}]
    client.close()


def test_responder_evento_requires_message():
    client = MCPClient(client=httpx.Client(transport=httpx.MockTransport(
        lambda request: pytest.fail("No request expected")
    )))

    with pytest.raises(ValueError, match="evento_id e mensagem"):
        client.responder_evento("evt-1")

    client.close()


def test_listar_eventos_registrar_conversa_and_catalog_use_mcp_tools():
    requests = []

    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        if body["method"] == "initialize":
            return httpx.Response(
                200,
                headers={"mcp-session-id": "session-123"},
                json={"jsonrpc": "2.0", "id": body["id"], "result": {}},
            )
        if body["method"] == "notifications/initialized":
            return httpx.Response(202)
        return _sse({
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {
                "content": [{"type": "text", "text": '{"status":"ok"}'}],
            },
        })

    client = MCPClient(client=httpx.Client(transport=httpx.MockTransport(handle)))
    client.listar_eventos(status="lido", limite=10, offset=5)
    client.registrar_conversa("executor", "Kit reservado", de="analista")
    client.registrar_conversa("executor", "Kit reservado", de="analista")
    client.consultar_catalogo_compra({"tipo": "notebook"}, limite=5)

    assert requests[2]["params"] == {
        "name": "listar_eventos",
        "arguments": {
            "agente": "orquestrador",
            "status": "lido",
            "limite": 10,
            "offset": 5,
        },
    }
    assert requests[3]["params"] == {
        "name": "registrar_conversa",
        "arguments": {
            "agente": "orquestrador",
            "para": "executor",
            "mensagem": "Kit reservado",
            "de": "analista",
        },
    }
    assert requests[4]["params"]["name"] == "consultar"
    assert requests[4]["params"]["arguments"]["base"] == "catalogo_compra"
    assert len(requests) == 5
    client.close()


def test_listar_eventos_validates_pagination():
    client = MCPClient(client=httpx.Client(transport=httpx.MockTransport(
        lambda request: pytest.fail("No request expected")
    )))

    with pytest.raises(ValueError, match="limite"):
        client.listar_eventos(limite=201)
    with pytest.raises(ValueError, match="offset"):
        client.listar_eventos(offset=-1)
    client.close()
