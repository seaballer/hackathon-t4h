# Análise: Conectar o Servidor MCP

## 📋 Resumo Executivo

Este documento analisa como conectar o servidor MCP (Streamable HTTP em `http://localhost:8765/mcp`) ao cliente LangGraph. O servidor é o "mundo" — ele não chama o agente, o agente chama o servidor.

**Status atual:** Cliente MCP implementado em `src/mcp_client.py`. O handshake
e `tools/list` foram validados contra o servidor ativo; JSON e SSE também estão
cobertos por testes com transporte simulado.

**Próximos passos:** Expandir a reconexão de sessão e validar operações de
escrita sem executar ações que dependem de aprovação humana.

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
| **Handshake** | Initialize → guardar Session-Id → initialized | ✅ Implementado e validado |
| **Session Management** | Reutilizar Session-Id, reconectar em falha | ⏳ Parcial |
| **Tool Calling** | Chamar ferramentas com envelope correto | ✅ Implementado |
| **Error Handling** | Retry para 503 e circuit breaker; demais status sem estratégia específica | ⏳ Parcial |
| **Idempotência** | Cache local em memória para algumas operações de escrita | ⏳ Parcial |

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
| **proximo_evento** | `agente`, `esperar_segundos` | evento ou `evento=null` / `encerrado` | Laço principal |
| **listar_eventos** | `agente`, `status`, `limite`, `offset` | eventos paginados | Histórico/backlog |
| **ler_evento** | `agente`, `evento_id` | evento completo | Detalhes de um evento |
| **responder_evento** | `agente`, `evento_id`, `mensagem` | confirmação | Responder ao remetente |
| **enviar_mensagem** | `agente`, `para`, `mensagem`; `assunto` opcional | confirmação | Notificações |
| **listar_bases** | `agente` | schemas e regras das bases | Descoberta de dados |
| **consultar** | `agente`, `base`, `filtro`, `busca`, `limite`, `offset` | registros paginados | Inventário, colaboradores, catálogo, etc |
| **registrar** | `agente`, `base`, `dados` | confirmação | Criar novo registro |
| **atualizar** | `agente`, `base`, `id`, `dados` | confirmação | Mudar estado |
| **registrar_conversa** | `agente`, `para`, `mensagem`; `de` opcional | confirmação | Deixar conversa visível no painel |

`catalogo_compra` é uma **base consultável** por `consultar(base="catalogo_compra")`,
não uma ferramenta MCP própria. A compra continua dependendo do portal do
fornecedor; não há ferramenta de compra no servidor MCP.

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

⚠️ **Idempotência limitada**
- Cache SHA-256 em memória para algumas operações de escrita.
- Não sobrevive a reinício do processo nem persiste estado `pendente/feito` em SQLite.

✅ **Timeout configurável**
- Padrão: 15 segundos
- Pode ser aumentado se usar `esperar_segundos`

### 4.2 Métodos disponíveis

```python
mcp = MCPClient(base_url="http://localhost:8765/mcp", timeout=15,
                agente="orquestrador")

# Laço principal
resposta = mcp.proximo_evento(esperar_segundos=30)

# Consultas
inventario = mcp.consultar("inventario", filtro={...})
eventos = mcp.listar_eventos(status="lido", limite=50)
catalogo = mcp.consultar_catalogo_compra()

# Atualizações
mcp.atualizar("inventario", "PAT-001", dados={...})

# Respostas
mcp.responder_evento("EVT-001", resposta="...")

# Mensagens
mcp.enviar_mensagem("andre@example.com", assunto="Aprovação", corpo="...")

# Registro de conversas
mcp.registrar_conversa(para="executor", mensagem="Kit reservado",
                       de="analista")
```

### 4.3 Execução de ações do plano

- `reservar_kit` e `registrar_entrada` reservam itens disponíveis já cadastrados
  no inventário para o colaborador. Sem itens explícitos, a entrada usa
  `kit_padrao` e `kit_extra_por_area` da base `regras`.
- `registrar_entrega_compra` só atualiza patrimônios existentes com status
  `em_transito`; o MCP não permite cadastrar novos itens no inventário.
- O catálogo pode ser consultado pela base `catalogo_compra`, mas não há
  ferramenta para efetuar compra. O portal do fornecedor segue fora do escopo.
- Ações com nível diferente de `FAZ_SOZINHO` ficam bloqueadas até existir um
  fluxo de aprovação humana.

---

## 5. O que Precisa Ser Validado/Implementado

### 5.1 Handshake Completo ✅

**Status:** Implementado em `src/mcp_client.py` e validado contra o servidor
ativo com `initialize`, `notifications/initialized` e `tools/list`.

### 5.2 Tratamento de SSE ✅

**Status:** O cliente aceita JSON e decodifica respostas SSE completas. A leitura
é bufferizada (`response.text`); não há consumo incremental de streams longos.

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
    mcp = MCPClient(agente="orquestrador")
    mcp.initialize()
    
    resposta = mcp.proximo_evento(esperar_segundos=5)
    
    assert resposta["status"] == "ok"
    assert "evento" in resposta or resposta.get("encerrado")

def test_consultar():
    """Testa se consultar retorna registros."""
    mcp = MCPClient(agente="estoque")
    mcp.initialize()
    
    resposta = mcp.consultar(
        "inventario",
        filtro={}
    )
    
    assert resposta["status"] == "ok"
    assert "registros" in resposta

def test_atualizar():
    """Testa se atualizar muda estado."""
    mcp = MCPClient(agente="estoque")
    mcp.initialize()
    
    resposta = mcp.atualizar(
        "inventario",
        "PAT-001",
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

### Fase 1: Handshake ✅

- [x] Implementar `initialize()`
- [x] Extrair e armazenar `Mcp-Session-Id`
- [x] Enviar `notifications/initialized`
- [x] Validar handshake com o servidor ativo

### Fase 2: Tratamento de SSE ✅

- [x] Detectar e decodificar respostas JSON e SSE completas
- [x] Cobrir SSE com transporte simulado
- [ ] Implementar leitura incremental de streams longos, se necessário

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

