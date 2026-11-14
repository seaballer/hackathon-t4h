# Agentes — Explicação Detalhada

Documentação completa sobre os 4 agentes que compõem o sistema de gestão de equipamentos.

---

## 1. COORDENADOR — O Maestro do Orquestrador

**Papel**: Gerencia o laço principal e o fluxo de eventos.

### O que faz

- **Aguarda eventos** chamando `proximo_evento(esperar_segundos=30)` continuamente
- **Inicializa o estado** na primeira execução (cache, pendências, erros)
- **Detecta encerramento** quando o servidor retorna `encerrado: true` (fim dos 22 dias)
- **Detecta virada de dia** comparando `data_simulada` e dispara "tick diário" (lógica futura)
- **Roteia para o Analista** quando há um evento novo
- **Volta ao loop** quando não há evento (aguarda 30 segundos)

### Responsabilidades específicas

```
┌─────────────────────────────────────────┐
│ COORDENADOR                             │
├─────────────────────────────────────────┤
│ ✅ Chamar proximo_evento em laço        │
│ ✅ Inicializar cache e pendências       │
│ ✅ Detectar encerramento                │
│ ✅ Detectar virada de dia               │
│ ✅ Rotear para Analista                 │
│ ✅ Tratar erros e logging               │
└─────────────────────────────────────────┘
```

### Fluxo

```
1. Chamar MCP: proximo_evento(esperar_segundos=30)
2. Se encerrado=true → marcar estado["encerrado"]=True → FIM
3. Se evento existe → carregar evento no estado → ir para ANALISTA
4. Se sem evento → verificar virada de dia → voltar ao passo 1
```

### Exemplo de saída

```python
state = {
    "evento_id": "PED-005",
    "evento": {
        "id": "PED-005",
        "de": "juliana.rocha@t4h.exemplo",
        "assunto": "Notebook com bateria estufada",
        "corpo": "Oi, meu notebook (EQ-0064) tá com a bateria estufada...",
        "chegou_em": "ter 02/12/2026 11:30",
        "status": "lido",
        "origem": "cenario"
    },
    "origem": "cenario",
    "data_simulada": "ter 02/12/2026 11:32",
    "cache": {...},
    "pendencias": {...}
}
```

---

## 2. ANALISTA — O Investigador Inteligente

**Papel**: Entende o evento e monta um plano de ações.

### O que faz

1. **Classifica o evento com LLM** (GPT-4o-mini)
   - Identifica um dos 12 tipos: `duvida`, `consulta_estoque`, `devolucao`, `alocacao`, `reserva_kit`, `troca_defeito`, `emprestimo`, `entrada_pessoa`, `saida_pessoa`, `baixa`, `entrega_compra`, `outro`
   - Extrai entidades: `patrimonio`, `colaborador_id`, `data`, `itens`, `valor`
   - Retorna confiança (0.0-1.0)

2. **Reanalisa se confiança < 0.7** (chamada LLM novamente com contexto)

3. **Resolve entidades consultando MCP**
   - Se há `patrimonio`, consulta inventário para obter status atual
   - Carrega dados do item (status, com_quem, etc)

4. **Monta plano de ações** baseado no tipo
   - Cada ação tem: `tool`, `args`, `motivo`, `nivel` (FAZ_SOZINHO/PROPOE/ESCALA)

### Responsabilidades específicas

```
┌─────────────────────────────────────────┐
│ ANALISTA                                │
├─────────────────────────────────────────┤
│ ✅ Classificar evento com LLM (12 tipos)│
│ ✅ Extrair entidades                    │
│ ✅ Reanalizar se confiança < 0.7        │
│ ✅ Resolver dados (consultar MCP)       │
│ ✅ Montar plano de ações                │
│ ✅ Atribuir níveis de autonomia         │
└─────────────────────────────────────────┘
```

### Exemplo: Evento de Devolução

```python
# Entrada
evento = {
    "assunto": "Devolvendo notebook EQ-0064",
    "corpo": "Oi, estou devolvendo o notebook que peguei emprestado..."
}

# Processamento
tipo = "devolucao"
confianca = 0.95
entidades = {
    "patrimonio": "EQ-0064",
    "colaborador_id": "C-019",
    "data": "2026-12-02"
}

# Plano montado
plano = [
    {
        "tool": "atualizar_inventario",
        "args": {"patrimonio": "EQ-0064", "status": "disponivel"},
        "motivo": "Marcar item como disponível",
        "nivel": "FAZ_SOZINHO"
    },
    {
        "tool": "responder_evento",
        "args": {"evento_id": "PED-005"},
        "motivo": "Confirmar devolução",
        "nivel": "FAZ_SOZINHO"
    }
]
```

### Exemplo: Evento de Alocação (com regra de negócio)

```python
# Entrada
evento = {
    "assunto": "Preciso de um notebook para projeto",
    "corpo": "Oi, preciso de um notebook para trabalhar no projeto X..."
}

# Processamento
tipo = "alocacao"
entidades = {
    "patrimonio": "EQ-0050",
    "valor": 3500.00,  # valor do notebook
    "item_atual": {"status": "disponivel"}
}

# Regra: se valor > R$ 500, precisa de aprovação
nivel = regras.nivel_autonomia("alocacao", 3500.00, True)
# → "PROPOE" (porque valor > 500)

plano = [
    {
        "tool": "atualizar_inventario",
        "args": {"patrimonio": "EQ-0050", "status": "reservado"},
        "motivo": "Reservar item",
        "nivel": "PROPOE"  # ← Precisa de aprovação!
    }
]
```

---

## 3. REVISOR — O Guardião das Regras

**Papel**: Valida o plano e atribui o nível final de autonomia.

### O que faz

1. **Bloqueia eventos de e-mail externo** (segurança)
   - Se `origem == "email_externo"` → bloqueia tudo

2. **Valida cada ação do plano**
   - Verifica se `patrimonio` existe
   - Verifica se `status` é válido
   - Verifica se `evento_id` existe
   - Verifica se `destinatário` é válido
   - Remove ações inválidas

3. **Detecta duplicidade** (simplificado, pode ser expandido)

4. **Atribui nível final**
   - Pega o nível máximo entre todas as ações
   - Ordem: FAZ_SOZINHO < PROPOE < ESCALA
   - Se há bloqueios, nível = ESCALA

### Responsabilidades específicas

```
┌─────────────────────────────────────────┐
│ REVISOR                                 │
├─────────────────────────────────────────┤
│ ✅ Validar regras de negócio            │
│ ✅ Bloquear e-mail externo              │
│ ✅ Validar cada ação                    │
│ ✅ Detectar duplicidade                 │
│ ✅ Atribuir nível final                 │
│ ✅ Registrar bloqueios                  │
└─────────────────────────────────────────┘
```

### Exemplo: Plano com Ações Mistas

```python
# Entrada
plano = [
    {
        "tool": "atualizar_inventario",
        "args": {"patrimonio": "EQ-0064", "status": "disponivel"},
        "nivel": "FAZ_SOZINHO"
    },
    {
        "tool": "atualizar_inventario",
        "args": {"patrimonio": "EQ-0050", "status": "reservado"},
        "nivel": "PROPOE"  # ← Nível mais alto
    },
    {
        "tool": "responder_evento",
        "args": {"evento_id": "PED-005"},
        "nivel": "FAZ_SOZINHO"
    }
]

# Processamento
# Todas as ações são válidas
# Nível máximo = PROPOE

# Saída
state["plano_aprovado"] = plano  # Todas as ações
state["nivel_final"] = "PROPOE"  # Nível mais alto
state["bloqueios"] = []  # Sem bloqueios
```

### Exemplo: Plano com Bloqueios

```python
# Entrada
plano = [
    {
        "tool": "atualizar_inventario",
        "args": {"patrimonio": None},  # ← Inválido!
        "nivel": "FAZ_SOZINHO"
    }
]

# Processamento
# Ação inválida: patrimonio não informado

# Saída
state["plano_aprovado"] = []  # Nenhuma ação
state["nivel_final"] = "ESCALA"  # Escala por falta de plano
state["bloqueios"] = ["Ação atualizar_inventario: Patrimonio não informado"]
```

---

## 4. EXECUTOR — O Operário Diligente

**Papel**: Executa o plano aprovado e registra os resultados.

### O que faz

1. **Executa cada ação do plano aprovado**
   - `responder_evento`: responde ao remetente
   - `enviar_mensagem`: envia e-mail
   - `atualizar_inventario`: atualiza status do item
   - `consultar_inventario`: consulta estoque
   - `registrar`: cria novo registro (nota: no Tema 3 retorna 405)
   - `atualizar`: altera registro existente

2. **Gera resposta ao remetente** usando LLM
   - Redige resposta personalizada baseada no tipo de evento
   - Usa entidades extraídas para contexto

3. **Registra cada ação executada**
   - Armazena: `tool`, `args`, `resultado`, `tokens` usados
   - Continua mesmo se uma ação falhar

4. **Trata erros graciosamente**
   - Se uma ação falha, registra erro e continua
   - Não interrompe o processamento

### Responsabilidades específicas

```
┌─────────────────────────────────────────┐
│ EXECUTOR                                │
├─────────────────────────────────────────┤
│ ✅ Executar cada ação do plano          │
│ ✅ Chamar MCP tools (responder, enviar) │
│ ✅ Atualizar inventário                 │
│ ✅ Gerar resposta ao remetente          │
│ ✅ Registrar ações feitas               │
│ ✅ Tratar erros sem parar               │
│ ✅ Rastrear tokens usados               │
└─────────────────────────────────────────┘
```

### Exemplo: Execução de Devolução

```python
# Entrada
plano_aprovado = [
    {
        "tool": "atualizar_inventario",
        "args": {"patrimonio": "EQ-0064", "status": "disponivel"},
        "motivo": "Marcar item como disponível",
        "nivel": "FAZ_SOZINHO"
    },
    {
        "tool": "responder_evento",
        "args": {"evento_id": "PED-005"},
        "motivo": "Confirmar devolução",
        "nivel": "FAZ_SOZINHO"
    }
]

# Processamento
# 1. Atualizar inventário
resultado1 = mcp.atualizar_inventario("EQ-0064", {"status": "disponivel"})
# → {"status": "ok", "patrimonio": "EQ-0064", "status_novo": "disponivel"}

# 2. Responder evento
resposta = llm.redigir_resposta("devolucao", {...}, {})
# → "Obrigado por devolver o notebook. Recebemos com sucesso!"
resultado2 = mcp.responder_evento("PED-005", resposta)
# → {"status": "ok", "evento_id": "PED-005", "respondido": true}

# Saída
state["acoes_feitas"] = [
    {
        "tool": "atualizar_inventario",
        "args": {"patrimonio": "EQ-0064", "status": "disponivel"},
        "resultado": {"status": "ok", ...},
        "tokens": 45
    },
    {
        "tool": "responder_evento",
        "args": {"evento_id": "PED-005"},
        "resultado": {"status": "ok", ...},
        "tokens": 120
    }
]
state["resposta_remetente"] = "Obrigado por devolver o notebook. Recebemos com sucesso!"
```

---

## Fluxo Completo de um Evento

```
┌─────────────────────────────────────────────────────────────────┐
│ EVENTO: "Devolvendo notebook EQ-0064"                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ COORDENADOR                                                     │
│ • Chama proximo_evento()                                        │
│ • Recebe evento PED-005                                         │
│ • Carrega no estado                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ ANALISTA                                                        │
│ • Classifica: tipo = "devolucao"                                │
│ • Extrai: patrimonio = "EQ-0064"                                │
│ • Consulta MCP: status atual = "com_quem: C-019"                │
│ • Monta plano:                                                  │
│   - atualizar_inventario (FAZ_SOZINHO)                          │
│   - responder_evento (FAZ_SOZINHO)                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ REVISOR                                                         │
│ • Valida cada ação                                              │
│ • Nível máximo = FAZ_SOZINHO                                    │
│ • Aprova plano                                                  │
│ • plano_aprovado = [ação1, ação2]                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ EXECUTOR                                                        │
│ • Executa: atualizar_inventario("EQ-0064", "disponivel")        │
│ • Executa: responder_evento("PED-005", "Recebido com sucesso")  │
│ • Registra 2 ações feitas                                       │
│ • Gera resposta ao remetente                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    [Volta ao COORDENADOR]
                    [Aguarda próximo evento]
```

---

## Resumo das Responsabilidades

| Agente | Entrada | Processamento | Saída |
|--------|---------|---------------|-------|
| **Coordenador** | MCP (proximo_evento) | Laço, roteamento | evento_id, evento, data_simulada |
| **Analista** | evento | LLM, consultas MCP | tipo, entidades, plano |
| **Revisor** | plano | Validação, regras | plano_aprovado, nivel_final, bloqueios |
| **Executor** | plano_aprovado | Execução MCP, LLM | acoes_feitas, resposta_remetente |

---

## Referências

- [Regras de Negócio](REGRAS_NEGOCIO.md) — Limites, prazos, validações
- [Documentação Técnica](DOCUMENTACAO_TECNICA.md) — Contrato MCP, bases de dados
- [Código dos Agentes](../src/agents/) — Implementação em Python
