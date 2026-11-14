"""Cliente MCP Streamable HTTP para o servidor do mundo simulado."""

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional, Union

import httpx

logger = logging.getLogger(__name__)


class MCPClient:
    """Cliente JSON-RPC MCP com suporte a respostas JSON e SSE."""

    PROTOCOL_VERSION = "2024-11-05"

    def __init__(
        self,
        base_url: str = "http://localhost:8765/mcp",
        timeout: int = 15,
        max_retries: int = 4,
        agente: str = "orquestrador",
        client: Optional[httpx.Client] = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.agente = agente
        self.client = client or httpx.Client(timeout=timeout)
        self.session_id: Optional[str] = None
        self._request_id = 0
        self.cache_idempotencia: Dict[str, Any] = {}

        self.falhas_consecutivas = 0
        self.circuit_aberto = False
        self.tempo_circuit_aberto = 0.0

    def close(self) -> None:
        """Fecha o cliente HTTP."""
        self.client.close()

    def _verificar_circuit_breaker(self) -> bool:
        if self.circuit_aberto:
            if time.time() - self.tempo_circuit_aberto > 3:
                self.circuit_aberto = False
                self.falhas_consecutivas = 0
                logger.info("Circuit breaker fechado")
                return False
            return True
        return False

    def _registrar_falha(self) -> None:
        self.falhas_consecutivas += 1
        if self.falhas_consecutivas >= 5:
            self.circuit_aberto = True
            self.tempo_circuit_aberto = time.time()
            logger.warning("Circuit breaker aberto após 5 falhas consecutivas")

    def _registrar_sucesso(self) -> None:
        self.falhas_consecutivas = 0

    @staticmethod
    def _decode_response(response: httpx.Response) -> Dict[str, Any]:
        response.raise_for_status()
        if not response.content:
            return {}

        if "text/event-stream" in response.headers.get("content-type", ""):
            data_lines = [
                line[5:].strip()
                for line in response.text.splitlines()
                if line.startswith("data:")
            ]
            if not data_lines:
                raise RuntimeError("Resposta SSE do MCP não contém mensagem.")
            payload = "\n".join(data_lines)
        else:
            payload = response.text

        try:
            result = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Resposta do MCP não é JSON válido.") from exc

        if not isinstance(result, dict):
            raise RuntimeError("Resposta do MCP deve ser um objeto JSON.")
        return result

    def _post_rpc(
        self,
        payload: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
            headers["Mcp-Protocol-Version"] = self.PROTOCOL_VERSION

        response = self.client.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=timeout or self.timeout,
        )
        return self._decode_response(response)

    def initialize(self, agente: Optional[str] = None) -> None:
        """Abre uma sessão MCP e conclui o handshake."""
        if agente:
            self.agente = agente
        self.session_id = None
        self._request_id += 1

        response = self.client.post(
            self.base_url,
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            json={
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": self.PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": self.agente, "version": "1.0.0"},
                },
            },
            timeout=self.timeout,
        )
        result = self._decode_response(response)
        if "error" in result:
            raise RuntimeError(f"Falha ao inicializar sessão MCP: {result['error']}")

        self.session_id = response.headers.get("Mcp-Session-Id")
        if not self.session_id:
            raise RuntimeError("O servidor MCP não retornou Mcp-Session-Id.")

        try:
            self._post_rpc({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except Exception:
            self.session_id = None
            raise

        self._registrar_sucesso()
        logger.info("Sessão MCP inicializada para o agente %s", self.agente)

    def _ensure_initialized(self) -> None:
        if not self.session_id:
            self.initialize()

    def _rpc(self, method: str, params: Optional[Dict[str, Any]] = None,
             timeout: Optional[float] = None) -> Dict[str, Any]:
        if self._verificar_circuit_breaker():
            raise RuntimeError("Circuit breaker aberto")
        self._ensure_initialized()
        self._request_id += 1
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        delays = (0.5, 1, 2)
        for tentativa in range(self.max_retries):
            try:
                result = self._post_rpc(payload, timeout=timeout)
                if "error" in result:
                    raise RuntimeError(f"Erro JSON-RPC MCP: {result['error']}")
                self._registrar_sucesso()
                return result
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 503 and tentativa < self.max_retries - 1:
                    delay = delays[min(tentativa, len(delays) - 1)]
                    logger.warning("MCP retornou 503; nova tentativa em %ss", delay)
                    time.sleep(delay)
                    continue
                self._registrar_falha()
                raise
            except Exception:
                self._registrar_falha()
                raise

        raise RuntimeError("Falha ao enviar requisição MCP.")

    def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Chama uma ferramenta MCP e decodifica o conteúdo textual JSON."""
        args = dict(arguments)
        args.setdefault("agente", self.agente)
        result = self._rpc(
            "tools/call",
            {"name": name, "arguments": args},
            timeout=timeout,
        )
        tool_result = result.get("result", {})
        if tool_result.get("isError"):
            details = [
                item.get("text", "")
                for item in tool_result.get("content", [])
                if item.get("type") == "text"
            ]
            raise RuntimeError(
                f"Ferramenta MCP {name} falhou: {'; '.join(details) or tool_result}"
            )

        text = "\n".join(
            item.get("text", "")
            for item in tool_result.get("content", [])
            if item.get("type") == "text"
        )
        if not text:
            return tool_result
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return {"texto": text}
        if not isinstance(value, dict):
            return {"resultado": value}
        if value.get("status") == "erro":
            raise RuntimeError(
                f"Ferramenta MCP {name} retornou erro: "
                f"{value.get('mensagem', value)}"
            )
        return value

    @staticmethod
    def _idempotency_key(tool: str, arguments: Dict[str, Any]) -> str:
        serialized = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(f"{tool}:{serialized}".encode()).hexdigest()

    def proximo_evento(self, esperar_segundos: int = 30) -> Dict[str, Any]:
        """Obtém o próximo evento, aguardando até 30 segundos."""
        if not 0 <= esperar_segundos <= 30:
            raise ValueError("esperar_segundos deve estar entre 0 e 30.")
        return self.call_tool(
            "proximo_evento",
            {"esperar_segundos": esperar_segundos},
            timeout=max(self.timeout, esperar_segundos + 5),
        )

    def ler_evento(self, evento_id: str) -> Dict[str, Any]:
        return self.call_tool("ler_evento", {"evento_id": evento_id})

    def listar_bases(self) -> Dict[str, Any]:
        return self.call_tool("listar_bases", {})

    def responder_evento(
        self,
        evento: Union[str, Dict[str, Any]],
        resposta: Optional[str] = None,
        motivo: Optional[str] = None,
    ) -> Dict[str, Any]:
        if isinstance(evento, dict):
            args = dict(evento)
            evento_id = args.get("evento_id") or args.get("id")
            mensagem = args.get("mensagem") or args.get("resposta") or resposta
        else:
            evento_id = evento
            mensagem = resposta
            args = {}
        if not evento_id or not mensagem:
            raise ValueError("responder_evento exige evento_id e mensagem.")
        args.update({"evento_id": evento_id, "mensagem": mensagem})
        if motivo:
            args["motivo"] = motivo

        key = self._idempotency_key("responder_evento", args)
        if key not in self.cache_idempotencia:
            self.cache_idempotencia[key] = self.call_tool("responder_evento", args)
        return self.cache_idempotencia[key]

    def enviar_mensagem(self, destinatario: str, assunto: str, corpo: str,
                        evento_id: Optional[str] = None) -> Dict[str, Any]:
        args: Dict[str, Any] = {
            "para": destinatario,
            "assunto": assunto,
            "mensagem": corpo,
        }
        if evento_id:
            args["evento_id"] = evento_id
        key = self._idempotency_key("enviar_mensagem", args)
        if key not in self.cache_idempotencia:
            self.cache_idempotencia[key] = self.call_tool("enviar_mensagem", args)
        return self.cache_idempotencia[key]

    def listar_eventos(
        self,
        status: Optional[str] = None,
        limite: int = 50,
        offset: int = 0,
        motivo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lista eventos paginados, opcionalmente filtrados por status."""
        if not 1 <= limite <= 200:
            raise ValueError("limite deve estar entre 1 e 200.")
        if offset < 0:
            raise ValueError("offset não pode ser negativo.")

        args: Dict[str, Any] = {"limite": limite, "offset": offset}
        if status:
            args["status"] = status
        if motivo:
            args["motivo"] = motivo
        return self.call_tool("listar_eventos", args)

    def registrar_conversa(
        self,
        para: str,
        mensagem: str,
        de: Optional[str] = None,
        motivo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra uma conversa entre agentes no painel MCP."""
        if not para.strip() or not mensagem.strip():
            raise ValueError("registrar_conversa exige para e mensagem.")

        args: Dict[str, Any] = {"para": para, "mensagem": mensagem}
        if de:
            args["de"] = de
        if motivo:
            args["motivo"] = motivo

        key = self._idempotency_key("registrar_conversa", args)
        if key not in self.cache_idempotencia:
            self.cache_idempotencia[key] = self.call_tool("registrar_conversa", args)
        return self.cache_idempotencia[key]

    def consultar(
        self,
        base: str,
        filtro: Optional[Dict[str, Any]] = None,
        motivo: Optional[str] = None,
        *,
        busca: Optional[str] = None,
        limite: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Consulta uma base com filtros e paginação opcionais."""
        args: Dict[str, Any] = {"base": base}
        if filtro is not None:
            args["filtro"] = filtro
        if motivo:
            args["motivo"] = motivo
        if busca:
            args["busca"] = busca
        if limite is not None:
            if not 1 <= limite <= 100:
                raise ValueError("limite deve estar entre 1 e 100.")
            args["limite"] = limite
        if offset is not None:
            if offset < 0:
                raise ValueError("offset não pode ser negativo.")
            args["offset"] = offset
        return self.call_tool("consultar", args)

    def consultar_catalogo_compra(
        self,
        filtro: Optional[Dict[str, Any]] = None,
        busca: Optional[str] = None,
        limite: int = 20,
        offset: int = 0,
        motivo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Consulta a base do catálogo; compras ainda exigem o portal do fornecedor."""
        return self.consultar(
            "catalogo_compra",
            filtro,
            motivo,
            busca=busca,
            limite=limite,
            offset=offset,
        )

    def consultar_inventario(self, filtros: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resultado = self.consultar("inventario", filtros)
        resultado.setdefault("itens", resultado.get("registros", []))
        return resultado

    def consultar_colaborador(self, filtros: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        filtros = filtros or {}
        if "colaborador_id" in filtros:
            filtros = {**filtros, "id": filtros["colaborador_id"]}
            filtros.pop("colaborador_id")
        resultado = self.consultar("colaboradores", filtros)
        registros = resultado.get("registros", [])
        resultado.setdefault("colaborador", registros[0] if registros else None)
        return resultado

    def registrar(self, base: str, dados: Dict[str, Any],
                  evento_id: Optional[str] = None) -> Dict[str, Any]:
        args: Dict[str, Any] = {"base": base, "dados": dados}
        if evento_id:
            args["evento_id"] = evento_id
        key = self._idempotency_key("registrar", args)
        if key not in self.cache_idempotencia:
            self.cache_idempotencia[key] = self.call_tool("registrar", args)
        return self.cache_idempotencia[key]

    def atualizar(self, base: str, id_registro: str, dados: Dict[str, Any],
                  evento_id: Optional[str] = None) -> Dict[str, Any]:
        args: Dict[str, Any] = {"base": base, "id": id_registro, "dados": dados}
        if evento_id:
            args["evento_id"] = evento_id
        key = self._idempotency_key("atualizar", args)
        if key not in self.cache_idempotencia:
            self.cache_idempotencia[key] = self.call_tool("atualizar", args)
        return self.cache_idempotencia[key]
