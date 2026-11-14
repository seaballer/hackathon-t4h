# Análise: Conectar o Servidor MCP

## 📋 Resumo Executivo

Este documento analisa como conectar o servidor MCP (Streamable HTTP em `http://localhost:8765/mcp`) ao cliente LangGraph. O servidor é o "mundo" — ele não chama o agente, o agente chama o servidor.

**Status atual:** Cliente MCP implementado em `src/mcp_client.py` com retry, idempotência e circuit breaker.

**Próximos passos:** Validar handshake, testar ferramentas, implementar reconexão.

---

## 1. Arquitetura de Conexão

### 1.1 Fluxo de Inicialização

```
┌─────────────────────────────────────────────────────────────┐
│ Cliente LangGraph (seu repositório)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    [1. Initialize]
                    POST /mcp com
                    { "jsonrpc": "2.0",
                      "method": "initialize",
                      "params": {...} }
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Servidor MCP (http://localhost:8765/mcp)                   │
│ - Cria sessão                                               │
│ - Retorna Mcp-Session-Id no header                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    [2. Guardar Session-Id]
                    Usar em TODAS as requisições
                            ↓
                    [3. Enviar initialized]
                    POST /mcp com
                    { "jsonrpc": "2.0",
                      "method": "notifications/initialized" }
                            ↓
                    [4. Pronto para usar]
                    Chamar ferramentas com
                    { "jsonrpc": "2.0",
                      "method": "tools/call",
                      "params": {...} }
```

### 1.2 Componentes Necessários

| Componente | Responsabilidade | Status |
|-----------|-----------------|--------|
| **MCPClient** | HTTP client com retry, idempotência, circuit breaker | ✅ Implementado |
| **Handshake** | Initialize → guardar Session-Id → initialized | ⏳ Precisa validar |
| **Session Management** | Reutilizar Session-Id, reconectar em falha | ⏳ Parcial |
| **Tool Calling** | Chamar ferramentas com envelope correto | ✅ Implementado |
| **Error Handling** | Tratar falhas simuladas, retry, circuit breaker | ✅ Implementado |
| **Idempotência** | Cache baseado em evento_id + tool + args | ✅ Implementado |

---

## 2. Contrato MCP Detalhado

### 2.1 Headers Obrigatórios

```http
Accept: application/json, text/event-stream
Content-Type: application/json
Mcp-Session-Id: <valor retornado no initialize>
```

**Importante:** O servidor pode retornar:
- JSON puro: `{ "status": "ok", ... }`
- Server-Sent Events (SSE): `event: message\ndata: {...}`

O cliente precisa aceitar os dois formatos.

### 2.2 Envelope de Requisição

Todas as chamadas seguem o padrão JSON-RPC 2.0:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "proximo_evento",
    "arguments": {
      "agente": "orquestrador",
      "esperar_segundos": 30
    }
  }
}
```

**Campos obrigatórios em `arguments`:**
- `agente`: nome do agente (até 60 caracteres)
- `motivo`: opcional, aparece no painel

### 2.3 Envelope de Resposta

Sucesso (status 200):
```json
{
  "status": "ok",
  "resultado": {...},
  "agora": "seg 01/12/2026 09:10"
}
```

Erro (status 400+):
```json
{
  "status": "erro",
  "codigo": "FERRAMENTA_NAO_ENCONTRADA",
  "mensagem": "Ferramenta 'xyz' não existe",
  "agora": "seg 01/12/2026 09:10"
}
```

---

## 3. Ferramentas Disponíveis

### 3.1 Ferramentas Principais (10 total)

| Ferramenta | Entrada | Saída | Uso |
|-----------|---------|-------|-----|
| **proximo_evento** | `agente`, `esperar_segundos` | evento com `tipo`, `origem`, `dados` | Laço principal |
| **ler_evento** | `agente`, `evento_id` | evento completo | Detalhes de um evento |
| **listar_eventos** | `agente`, `filtro` | lista de eventos | Histórico |
| **consultar** | `agente`, `base`, `filtro` | registros | Inventário, colaboradores, etc |
| **atualizar** | `agente`, `base`, `chave`, `dados` | confirmação | Mudar estado |
| **responder_evento** | `agente`, `evento_id`, `resposta` | confirmação | Responder a dúvidas |
| **enviar_mensagem** | `agente`, `para`, `assunto`, `corpo` | confirmação | Notificações |
| **registrar** | `agente`, `base`, `dados` | confirmação | Criar novo registro |
| **registrar_conversa** | `agente`, `evento_id`, `participantes`, `resumo` | confirmação | Deixar visível no painel |
| **catalogo_compra** | `agente`, `filtro` | produtos | Buscar itens para compra |

### 3.2 Exemplo: proximo_evento

```python
# Requisição
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "proximo_evento",
    "arguments": {
      "agente": "orquestrador",
      "esperar_segundos": 30
    }
  }
}

# Resposta (sucesso)
{
  "status": "ok",
  "resultado": {
    "evento_id": "EVT-001",
    "tipo": "duvida",
    "origem": "email",
    "dados": {
      "remetente": "andre@example.com",
      "assunto": "Onde está meu notebook?",
      "corpo": "..."
    },
    "encerrado": false
  },
  "agora": "seg 01/12/2026 09:10"
}

# Resposta (encerrado)
{
  "status": "ok",
  "resultado": {
    "encerrado": true,
    "resumo": "Simulação encerrada após 22 dias"
  },
  "agora": "seg 01/12/2026 09:10"
}
```

---

## 4. Implementação Atual (src/mcp_client.py)

### 4.1 O que está implementado

✅ **Retry com backoff exponencial**
- Tentativas: 0.5s, 1s, 2s
- Máximo: 4 tentativas
- Reseta em sucesso

✅ **Circuit breaker**
- Abre após 5 falhas consecutivas
- Fecha após 3 segundos
- Previne cascata de falhas

✅ **Idempotência**
- Cache baseado em MD5(evento_id + tool + args)
- Evita duplicação de efeitos
- Importante para operações críticas

✅ **Timeout configurável**
- Padrão: 15 segundos
- Pode ser aumentado se usar `esperar_segundos`

### 4.2 Métodos disponíveis

```python
mcp = MCPClient(base_url="http://localhost:8765/mcp", timeout=15)

# Laço principal
resposta = mcp.proximo_evento(agente="orquestrador", esperar_segundos=30)

# Consultas
inventario = mcp.consultar(agente="estoque", base="inventario", filtro={...})

# Atualizações
mcp.atualizar(agente="estoque", base="inventario", chave="PAT-001", dados={...})

# Respostas
mcp.responder_evento(agente="atendimento", evento_id="EVT-001", resposta="...")

# Mensagens
mcp.enviar_mensagem(agente="supervisor", para="andre@example.com", 
                    assunto="Aprovação", corpo="...")

# Registro de conversas
mcp.registrar_conversa(agente="orquestrador", evento_id="EVT-001",
                       participantes=["orquestrador", "estoque"],
                       resumo="Decidimos aprovar a compra")
```

---

## 5. O que Precisa Ser Validado/Implementado

### 5.1 Handshake Completo ⏳

**Status:** Parcialmente implementado

**O que falta:**
1. Método `initialize()` que:
   - Envia `{ "method": "initialize", "params": {...} }`
   - Extrai `Mcp-Session-Id` do header
   - Armazena para usar em todas as requisições

2. Método `send_initialized()` que:
   - Envia `{ "method": "notifications/initialized" }`
   - Confirma que o cliente está pronto

3. Reconexão automática:
   - Se Session-Id expirar, refazer handshake
   - Detectar quando servidor reinicia

**Código necessário:**

```python
class MCPClient:
    def __init__(self, base_url: str, timeout: int = 15):
        self.base_url = base_url
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self.client = httpx.Client(timeout=timeout)
    
    def initialize(self, agente: str) -> bool:
        """Faz handshake com o servidor MCP."""
        try:
            response = self.client.post(
                f"{self.base_url}",
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": agente,
                            "version": "1.0.0"
                        }
                    }
                }
            )
            
            # Extrair Session-Id do header
            self.session_id = response.headers.get("Mcp-Session-Id")
            if not self.session_id:
                logger.error("Servidor não retornou Mcp-Session-Id")
                return False
            
            logger.info(f"Handshake bem-sucedido. Session-Id: {self.session_id}")
            
            # Enviar initialized
            return self.send_initialized()
        
        except Exception as e:
            logger.error(f"Erro no initialize: {e}")
            return False
    
    def send_initialized(self) -> bool:
        """Notifica ao servidor que o cliente está pronto."""
        try:
            response = self.client.post(
                f"{self.base_url}",
                json={
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                },
                headers={"Mcp-Session-Id": self.session_id}
            )
            
            if response.status_code == 202:
                logger.info("Servidor confirmou initialized")
                return True
            
            logger.warning(f"Resposta inesperada: {response.status_code}")
            return False
        
        except Exception as e:
            logger.error(f"Erro ao enviar initialized: {e}")
            return False
    
    def _fazer_requisicao(self, method: str, endpoint: str, data: Dict) -> Dict:
        """Adiciona Session-Id a todas as requisições."""
        headers = {}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        
        # ... resto do código de retry ...
```

### 5.2 Tratamento de SSE ⏳

**Status:** Não implementado

**O problema:** O servidor pode retornar Server-Sent Events em vez de JSON puro.

**Formato SSE:**
```
event: message
data: {"status": "ok", "resultado": {...}}

event: message
data: {"status": "ok", "resultado": {...}}
```

**Solução:** Usar `httpx.stream()` para ler SSE:

```python
def _fazer_requisicao_stream(self, endpoint: str, data: Dict) -> Dict:
    """Faz requisição e lida com SSE."""
    url = f"{self.base_url}{endpoint}"
    headers = {"Mcp-Session-Id": self.session_id} if self.session_id else {}
    
    with self.client.stream("POST", url, json=data, headers=headers) as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                json_str = line[6:]  # Remove "data: "
                return json.loads(json_str)
    
    raise Exception("Nenhuma resposta recebida")
```

### 5.3 Reconexão Automática ⏳

**Status:** Não implementado

**Cenário:** Servidor reinicia, Session-Id expira

**Solução:**

```python
def _fazer_requisicao(self, method: str, endpoint: str, data: Dict) -> Dict:
    """Faz requisição com reconexão automática."""
    
    # Tentar com Session-Id atual
    try:
        return self._tentar_requisicao(method, endpoint, data)
    except SessionExpiredError:
        logger.warning("Session expirada, reconectando...")
        
        # Refazer handshake
        if not self.initialize(agente=self.agente_nome):
            raise Exception("Falha ao reconectar")
        
        # Tentar novamente
        return self._tentar_requisicao(method, endpoint, data)
```

### 5.4 Validação de Ferramentas ⏳

**Status:** Parcialmente implementado

**O que falta:**
- Testar cada ferramenta com dados reais
- Validar envelopes de requisição/resposta
- Testar tratamento de erros

**Checklist de testes:**

```python
def test_proximo_evento():
    """Testa se proximo_evento retorna evento válido."""
    mcp = MCPClient()
    mcp.initialize(agente="orquestrador")
    
    resposta = mcp.proximo_evento(agente="orquestrador", esperar_segundos=5)
    
    assert resposta["status"] == "ok"
    assert "resultado" in resposta
    assert "evento_id" in resposta["resultado"] or resposta["resultado"].get("encerrado")

def test_consultar():
    """Testa se consultar retorna registros."""
    mcp = MCPClient()
    mcp.initialize(agente="estoque")
    
    resposta = mcp.consultar(
        agente="estoque",
        base="inventario",
        filtro={}
    )
    
    assert resposta["status"] == "ok"
    assert "registros" in resposta["resultado"]

def test_atualizar():
    """Testa se atualizar muda estado."""
    mcp = MCPClient()
    mcp.initialize(agente="estoque")
    
    resposta = mcp.atualizar(
        agente="estoque",
        base="inventario",
        chave="PAT-001",
        dados={"estado": "em_uso"}
    )
    
    assert resposta["status"] == "ok"
```

---

## 6. Integração com LangGraph

### 6.1 Fluxo de Inicialização

```python
# main.py
from src.mcp_client import MCPClient
from src.graph import criar_grafo

def main():
    # 1. Conectar ao MCP
    mcp = MCPClient(base_url="http://localhost:8765/mcp", timeout=40)
    
    if not mcp.initialize(agente="orquestrador"):
        logger.error("Falha ao conectar ao MCP")
        return
    
    # 2. Criar grafo
    llm = LLMClient()
    clock = Clock()
    regras = RegrasEquipamentos()
    
    graph = criar_grafo(mcp, llm, clock, regras)
    
    # 3. Executar laço
    config = {"configurable": {"thread_id": "main"}}
    
    while True:
        try:
            # Executar um ciclo
            state = graph.invoke(
                {"evento_id": None, "evento": None},
                config=config
            )
            
            # Verificar se encerrou
            if state.get("encerrado"):
                logger.info("Simulação encerrada")
                break
        
        except Exception as e:
            logger.error(f"Erro no ciclo: {e}")
            # Reconectar se necessário
            if not mcp.initialize(agente="orquestrador"):
                break
```

### 6.2 Nó: Aguardar Evento

```python
# src/nodes/aguardar_evento.py
def node(state: AgentState, mcp: MCPClient, clock: Clock) -> AgentState:
    """Aguarda próximo evento do MCP."""
    
    logger.info("Aguardando próximo evento...")
    
    try:
        resposta = mcp.proximo_evento(
            agente="orquestrador",
            esperar_segundos=30
        )
        
        if resposta["status"] != "ok":
            logger.error(f"Erro ao buscar evento: {resposta}")
            state["erros"].append(resposta.get("mensagem", "Erro desconhecido"))
            return state
        
        resultado = resposta["resultado"]
        
        # Verificar se encerrou
        if resultado.get("encerrado"):
            logger.info("Simulação encerrada")
            state["encerrado"] = True
            return state
        
        # Novo evento
        evento = resultado
        state["evento_id"] = evento["evento_id"]
        state["evento"] = evento
        state["tipo"] = evento.get("tipo")
        
        logger.info(f"Evento recebido: {evento['evento_id']} ({evento.get('tipo')})")
        
        return state
    
    except Exception as e:
        logger.error(f"Erro ao aguardar evento: {e}")
        state["erros"].append(str(e))
        return state
```

---

## 7. Checklist de Implementação

### Fase 1: Handshake ✅ → ⏳

- [ ] Implementar `initialize(agente: str) -> bool`
- [ ] Implementar `send_initialized() -> bool`
- [ ] Extrair e armazenar `Mcp-Session-Id`
- [ ] Testar handshake com servidor real
- [ ] Adicionar logging detalhado

### Fase 2: Tratamento de SSE ⏳

- [ ] Implementar `_fazer_requisicao_stream()`
- [ ] Detectar formato de resposta (JSON vs SSE)
- [ ] Testar com servidor em modo SSE
- [ ] Adicionar timeout para SSE

### Fase 3: Reconexão ⏳

- [ ] Detectar Session-Id expirada
- [ ] Refazer handshake automaticamente
- [ ] Testar com servidor reiniciando
- [ ] Adicionar backoff para reconexão

### Fase 4: Validação de Ferramentas ⏳

- [ ] Testar `proximo_evento`
- [ ] Testar `consultar`
- [ ] Testar `atualizar`
- [ ] Testar `responder_evento`
- [ ] Testar `enviar_mensagem`
- [ ] Testar `registrar_conversa`
- [ ] Testar tratamento de erros

### Fase 5: Integração com LangGraph ⏳

- [ ] Atualizar `main.py` com inicialização MCP
- [ ] Atualizar nó `aguardar_evento`
- [ ] Atualizar nó `resolver_dados`
- [ ] Atualizar nó `executar`
- [ ] Testar fluxo completo

---

## 8. Próximos Passos

1. **Validar servidor MCP está rodando**
   ```bash
   curl -X POST http://localhost:8765/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "initialize", "params": {}}'
   ```

2. **Implementar handshake completo** em `src/mcp_client.py`

3. **Testar com servidor real** usando `pytest tests/test_mcp_connection.py`

4. **Integrar com LangGraph** atualizando `main.py` e nós

5. **Executar fluxo completo** e validar estado final

---

## 9. Referências

- **Documentação técnica:** `docs/DOCUMENTACAO_TECNICA.md`
- **Cliente MCP atual:** `src/mcp_client.py`
- **Nós LangGraph:** `src/nodes/`
- **Testes:** `tests/test_mcp_connection.py` (a criar)

