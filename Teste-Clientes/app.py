import json
import time
import httpx

MCP_URL = "http://localhost:8765/mcp"


class MCPError(Exception):
    def __init__(self, data: dict):
        super().__init__(data.get("mensagem", "Erro desconhecido no servidor MCP"))
        self.data = data
        self.codigo = data.get("codigo")


class ClienteMCP:
    def __init__(self, url: str, agente: str, timeout: float = 40.0):
        self.url = url
        self.agente = agente
        # Timeout precisa ser maior que esperar_segundos (25s) + falhas lentas (até 9s)
        self.http = httpx.Client(timeout=timeout)
        self.session_id: str | None = None
        self.req_id = 0
        self._conectar()

    def _post(self, payload: dict) -> dict | None:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        resp = self.http.post(self.url, json=payload, headers=headers)
        resp.raise_for_status()

        # Captura o ID da sessão retornado no initialize
        if sid := resp.headers.get("Mcp-Session-Id"):
            self.session_id = sid

        if resp.status_code == 202 or not resp.content:
            return None

        # O servidor pode responder via SSE ou JSON puro
        content_type = resp.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:].strip())
            return None

        return resp.json()

    def _rpc(self, method: str, params: dict) -> dict:
        self.req_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self.req_id,
            "method": method,
            "params": params,
        }
        data = self._post(payload)
        if data is None:
            raise RuntimeError(
                f"Sem resposta do servidor para o método {method}")
        if "error" in data:
            raise RuntimeError(f"Erro JSON-RPC: {data['error']}")
        return data["result"]

    def _conectar(self) -> None:
        print(f"[{self.agente}] Iniciando handshake com {self.url}...")
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": self.agente, "version": "0.1.0"},
            },
        )
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        print(f"[{self.agente}] Conectado! Session ID: {self.session_id}")

    def chamar_ferramenta(self, nome: str, tentativas: int = 3, **args) -> dict:
        args["agente"] = self.agente

        for tentativa in range(tentativas):
            try:
                result = self._rpc(
                    "tools/call", {"name": nome, "arguments": args})
                texto = result["content"][0]["text"]
                data = json.loads(texto)

                if result.get("isError") or data.get("status") == "erro":
                    raise MCPError(data)

                return data

            except MCPError as e:
                # Retry automático apenas para indisponibilidade simulada (503)
                if e.codigo == 503 and tentativa < tentativas - 1:
                    espera = 1.5 * (tentativa + 1)
                    print(
                        f"[{self.agente}] Erro 503 simulado. Tentando novamente em {espera}s...")
                    time.sleep(espera)
                    continue
                raise
            except httpx.HTTPStatusError as e:
                # Se o servidor reiniciar, a sessão expira (400/404); refaz handshake
                if e.response.status_code in (400, 404) and tentativa < tentativas - 1:
                    print(f"[{self.agente}] Sessão perdida. Reconectando...")
                    self.session_id = None
                    self._conectar()
                    continue
                raise


def main():
    # Instancia o cliente principal
    orquestrador = ClienteMCP(MCP_URL, agente="orquestrador")

    # 1. Valida conexão listando as bases disponíveis
    bases = orquestrador.chamar_ferramenta(
        "listar_bases", motivo="Verificar contrato inicial")
    print(f"\nBases carregadas: {[b['base'] for b in bases.get('bases', [])]}")

    # 2. Exemplo de consulta rápida ao inventário
    livres = orquestrador.chamar_ferramenta(
        "consultar",
        base="inventario",
        filtro={"status": "disponivel"},
        motivo="Contagem inicial de estoque livre",
    )
    print(f"Itens disponíveis no início: {livres['total']}\n")

    # 3. Laço principal de consumo de eventos
    print("Aguardando eventos do cenário...")
    while True:
        try:
            res = orquestrador.chamar_ferramenta(
                "proximo_evento",
                esperar_segundos=25,
                motivo="Buscar próximo evento na fila",
            )

            if res.get("encerrado"):
                print("\n[FIM] Cenário encerrado pelo servidor!")
                break

            evento = res.get("evento")
            if not evento:
                prox = res.get("proximo_evento_do_cenario", {})
                print(
                    f"[{res.get('agora')}] Nenhum evento agora. Próximo em ~{prox.get('em_segundos_reais', '?')}s...")
                continue

            print(f"\n--- NOVO EVENTO ({res.get('agora')}) ---")
            print(f"ID:      {evento['id']}")
            print(f"De:      {evento['nome']} <{evento['de']}>")
            print(f"Assunto: {evento['assunto']}")
            print(f"Corpo:   {evento['corpo']}")

            # Exemplo de coordenação visível no painel
            orquestrador.chamar_ferramenta(
                "registrar_conversa",
                para="atendimento",
                mensagem=f"Recebi o evento {evento['id']}. Analisando solicitação...",
            )

            # Resposta simples de confirmação para demonstrar ação vinculada ao evento_id
            orquestrador.chamar_ferramenta(
                "responder_evento",
                evento_id=evento["id"],
                mensagem="Olá! Recebemos sua solicitação e nossa equipe já está verificando no inventário.",
                motivo="Confirmar recebimento do chamado",
            )
            print(f"-> Evento {evento['id']} respondido com sucesso.")

        except MCPError as e:
            if e.codigo == 410:
                print("\n[FIM] Servidor retornou 410 (cenário já finalizado).")
                break
            print(f"[ERRO DE REGRA {e.codigo}] {e}")
        except KeyboardInterrupt:
            print("\nEncerrando cliente manualmente.")
            break


if __name__ == "__main__":
    main()
