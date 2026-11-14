# Fluxo de Processamento — Colaborador Digital

## Diagrama Geral

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SERVIDOR MCP                                    │
│  • Eventos (proximo_evento, ler_evento)                                 │
│  • Inventário (consultar, atualizar)                                    │
│  • Mensagens (responder_evento, enviar_mensagem)                        │
│  • Registros (registrar, atualizar)                                     │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ HTTP MCP
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                    TIME DE AGENTES (LangGraph)                          │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ COORDENADOR                                                      │  │
│  │ • proximo_evento() em laço                                       │  │
│  │ • Detecção de virada de dia                                     │  │
│  │ • Roteamento para Analista                                      │  │
│  │ • Detecção de encerramento                                      │  │
│  └──────────────────────┬───────────────────────────────────────────┘  │
│                         │                                               │
│                         ↓                                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ ANALISTA                                                         │  │
│  │ • Classificação com LLM (12 tipos)                               │  │
│  │ • Extração de entidades                                          │  │
│  │ • Resolução de dados (consulta MCP)                              │  │
│  │ • Montagem de plano de ações                                     │  │
│  │ • Reanalise se confiança < 0.7                                   │  │
│  └──────────────────────┬───────────────────────────────────────────┘  │
│                         │                                               │
│                         ↓                                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ REVISOR                                                          │  │
│  │ • Validação de regras de negócio                                 │  │
│  │ • Atribuição de nível final (FAZ/PROPÕE/ESCALA)                  │  │
│  │ • Bloqueio de e-mail externo                                     │  │
│  │ • Detecção de duplicidade                                        │  │
│  └──────────────────────┬───────────────────────────────────────────┘  │
│                         │                                               │
│                         ↓                                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ EXECUTOR                                                         │  │
│  │ • Execução de ações do plano                                     │  │
│  │ • Atualização de inventário                                      │  │
│  │ • Resposta a eventos                                             │  │
│  │ • Envio de mensagens                                             │  │
│  │ • Registro de ações feitas                                       │  │
│  └──────────────────────┬───────────────────────────────────────────┘  │
│                         │                                               │
│                         └──────────────────┐                            │
│                                            │                            │
│                                            ↓                            │
│                                    [volta ao COORDENADOR]               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Fluxo Detalhado por Tipo de Evento

### 1. DÚVIDA

```
Evento: "Como faço para solicitar um notebook?"

COORDENADOR
  └─→ proximo_evento() → evento_id: EVT-001

ANALISTA
  └─→ LLM classifica: tipo="duvida", confianca=0.95
  └─→ Plano: [responder_evento]

REVISOR
  └─→ Valida: OK
  └─→ Nível final: FAZ_SOZINHO

EXECUTOR
  └─→ responder_evento(EVT-001, "Você pode solicitar via portal...")
  └─→ Registra ação feita

COORDENADOR
  └─→ Volta ao laço
```

---

### 2. ALOCAÇÃO COM ESTOQUE

```
Evento: "Alocar notebook para João Silva"

COORDENADOR
  └─→ proximo_evento() → evento_id: EVT-002

ANALISTA
  └─→ LLM classifica: tipo="alocacao"
  └─→ Extrai: colaborador_id="JOAO-001", patrimonio="PAT-123"
  └─→ Consulta MCP: inventario[PAT-123].status = "disponivel"
  └─→ Plano: [atualizar_inventario(status="reservado"), responder_evento]

REVISOR
  └─→ Valida: OK
  └─→ Nível final: FAZ_SOZINHO (tem estoque)

EXECUTOR
  └─→ atualizar_inventario(PAT-123, status="reservado")
  └─→ responder_evento(EVT-002, "Notebook alocado para João")
  └─→ Registra 2 ações feitas

COORDENADOR
  └─→ Volta ao laço
```

---

### 3. ALOCAÇÃO SEM ESTOQUE (VALOR BAIXO)

```
Evento: "Alocar mouse para Maria Santos"

COORDENADOR
  └─→ proximo_evento() → evento_id: EVT-003

ANALISTA
  └─→ LLM classifica: tipo="alocacao"
  └─→ Extrai: colaborador_id="MARIA-001", patrimonio="PAT-456"
  └─→ Consulta MCP: inventario[PAT-456].status = "indisponivel"
  └─→ Consulta catalogo: mouse custa R$ 150
  └─→ Plano: [comprar_portal(valor=150), atualizar_inventario, responder_evento]

REVISOR
  └─→ Valida: OK
  └─→ Nível final: FAZ_SOZINHO (valor < R$ 500)

EXECUTOR
  └─→ comprar_portal(PAT-456, valor=150) [Playwright]
  └─→ atualizar_inventario(PAT-456, status="em_transito")
  └─→ responder_evento(EVT-003, "Compra realizada, chegará em 3 dias")
  └─→ Registra 3 ações feitas

COORDENADOR
  └─→ Volta ao laço
```

---

### 4. ALOCAÇÃO SEM ESTOQUE (VALOR ALTO)

```
Evento: "Alocar servidor para TI"

COORDENADOR
  └─→ proximo_evento() → evento_id: EVT-004

ANALISTA
  └─→ LLM classifica: tipo="alocacao"
  └─→ Extrai: colaborador_id="TI-001", patrimonio="PAT-789"
  └─→ Consulta MCP: inventario[PAT-789].status = "indisponivel"
  └─→ Consulta catalogo: servidor custa R$ 8.000
  └─→ Plano: [criar_fila_aprovacao, responder_evento]

REVISOR
  └─→ Valida: OK
  └─→ Nível final: PROPÕE (valor > R$ 500)

EXECUTOR
  └─→ criar_fila_aprovacao(EVT-004, valor=8000, motivo="Servidor para TI")
  └─→ responder_evento(EVT-004, "Solicitação enviada para aprovação")
  └─→ Registra 2 ações feitas

[Humano aprova via API]

COORDENADOR
  └─→ Recebe evento de aprovação
  └─→ Volta ao laço
```

---

### 5. DEVOLUÇÃO

```
Evento: "Devolvendo notebook PAT-123"

COORDENADOR
  └─→ proximo_evento() → evento_id: EVT-005

ANALISTA
  └─→ LLM classifica: tipo="devolucao"
  └─→ Extrai: patrimonio="PAT-123"
  └─→ Consulta MCP: inventario[PAT-123].status = "alocado"
  └─→ Plano: [atualizar_inventario(status="disponivel"), responder_evento]

REVISOR
  └─→ Valida: OK (item está alocado)
  └─→ Nível final: FAZ_SOZINHO

EXECUTOR
  └─→ atualizar_inventario(PAT-123, status="disponivel")
  └─→ responder_evento(EVT-005, "Devolução registrada")
  └─→ Registra 2 ações feitas

COORDENADOR
  └─→ Volta ao laço
```

---

### 6. COBRANÇA DE DEVOLUÇÃO (TICK DIÁRIO)

```
[Virada de dia detectada]

COORDENADOR
  └─→ Detecta: data_simulada mudou
  └─→ Dispara: tick_diario()
  └─→ Verifica: saidas com > 5 dias úteis sem devolução
  └─→ Cria evento: tipo="saida_pessoa", dias_uteis=7

ANALISTA
  └─→ LLM classifica: tipo="saida_pessoa"
  └─→ Extrai: colaborador_id="JOAO-001"
  └─→ Plano: [enviar_mensagem(assunto="Devolução de equipamentos")]

REVISOR
  └─→ Valida: OK
  └─→ Nível final: FAZ_SOZINHO

EXECUTOR
  └─→ enviar_mensagem(JOAO-001, "Por favor, devolva os equipamentos")
  └─→ Registra 1 ação feita

COORDENADOR
  └─→ Volta ao laço
```

---

### 7. BAIXA (ESCALA)

```
Evento: "Baixar notebook PAT-999 (quebrado)"

COORDENADOR
  └─→ proximo_evento() → evento_id: EVT-007

ANALISTA
  └─→ LLM classifica: tipo="baixa"
  └─→ Extrai: patrimonio="PAT-999"
  └─→ Consulta MCP: inventario[PAT-999].status = "quebrado"
  └─→ Plano: [atualizar_inventario(status="baixado")]

REVISOR
  └─→ Valida: OK (item está quebrado)
  └─→ Nível final: ESCALA (requer aprovação)

EXECUTOR
  └─→ criar_fila_escalados(EVT-007, motivo="Baixa de item quebrado")
  └─→ responder_evento(EVT-007, "Solicitação enviada para aprovação")
  └─→ Registra 2 ações feitas

[Humano aprova via API]

COORDENADOR
  └─→ Recebe evento de aprovação
  └─→ Volta ao laço
```

---

## Tratamento de Erros

### Erro 503 (Service Unavailable)

```
EXECUTOR
  └─→ atualizar_inventario() → 503
  └─→ Retry 1: aguarda 0.5s → 503
  └─→ Retry 2: aguarda 1s → 503
  └─→ Retry 3: aguarda 2s → 200 OK
  └─→ Ação executada com sucesso
```

### Erro 504 (Gateway Timeout)

```
EXECUTOR
  └─→ responder_evento() → 504
  └─→ Verifica: ler_evento(EVT-001) → já respondido
  └─→ Não repete (idempotência)
  └─→ Registra como sucesso
```

### Erro 409 (Conflict)

```
EXECUTOR
  └─→ atualizar_inventario(PAT-123, status="reservado") → 409
  └─→ Reconsulta: inventario[PAT-123] → status="alocado"
  └─→ Revalida regra: pode alocar sobre alocado? NÃO
  └─→ Replanejar: ESCALA
```

### Circuit Breaker

```
EXECUTOR
  └─→ Falha 1: 503
  └─→ Falha 2: 503
  └─→ Falha 3: 503
  └─→ Falha 4: 503
  └─→ Falha 5: 503
  └─→ Circuit breaker ABERTO
  └─→ Aguarda 3s
  └─→ Circuit breaker FECHADO
  └─→ Retry continua
```

---

## Checkpoint e Persistência

```
Evento EVT-001 recebido
  └─→ Checkpoint: thread_id="EVT-001", estado inicial
  └─→ Coordenador processa
  └─→ Checkpoint: estado após Coordenador
  └─→ Analista processa
  └─→ Checkpoint: estado após Analista
  └─→ Revisor processa
  └─→ Checkpoint: estado após Revisor
  └─→ Executor processa
  └─→ Checkpoint: estado final

[Se falhar em qualquer ponto]
  └─→ Recupera do último checkpoint
  └─→ Continua de onde parou
```

---

## Métricas e Logging

```
Cada ação registra:
  • timestamp
  • evento_id
  • tool executada
  • args
  • resultado
  • tokens LLM usados
  • tempo de execução

Ao final:
  • Total de eventos processados
  • Total de tokens LLM
  • Total de erros
  • Taxa de sucesso
```

---

## Resumo

1. **Coordenador** puxa eventos em laço
2. **Analista** classifica e monta plano
3. **Revisor** valida e atribui nível
4. **Executor** executa e registra
5. **Volta ao Coordenador** (loop)

Cada passo é resiliente, idempotente e persistido em checkpoint.

---

**Fluxo completo: ~5-10 segundos por evento (dependendo da complexidade)**
