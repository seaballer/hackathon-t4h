# Colaborador Digital — Gestão de Equipamentos

Time de agentes de IA para automação de gestão de equipamentos de TI no Hackathon UNIFEI 2026.

## Arquitetura

```
Coordenador (laço principal, tick diário, backlog)
    ↓
Analista (classificação LLM, extração de entidades, plano)
    ↓
Revisor (validação de regras, atribuição de nível)
    ↓
Executor (execução de ações, atualização de inventário)
    ↓
[volta ao Coordenador]
```

## Estrutura de Arquivos

```
colaborador-digital-equipamentos/
├── src/
│   ├── __init__.py
│   ├── state.py           # TypedDict do estado compartilhado
│   ├── clock.py           # Relógio simulado e dias úteis
│   ├── rules.py           # Regras de negócio (puro Python)
│   ├── llm.py             # Cliente OpenAI com cache e fallback
│   ├── mcp_client.py      # Cliente MCP com retry e idempotência
│   ├── graph.py           # Grafo LangGraph
│   └── agents/
│       ├── __init__.py
│       ├── coordenador.py # Coordenador
│       ├── analista.py    # Analista
│       ├── revisor.py     # Revisor
│       └── executor.py    # Executor
├── tests/
│   └── test_*.py
├── main.py                # Ponto de entrada
├── requirements.txt       # Dependências
├── .env.example          # Exemplo de variáveis de ambiente
├── .gitignore
└── README.md
```

## Instalação

### Pré-requisitos

- Python 3.11+
- Servidor MCP rodando em `http://localhost:8765/mcp`
- Chave da API OpenAI

### Passos

1. **Clonar ou copiar o projeto**

```bash
cd colaborador-digital-equipamentos
```

2. **Criar ambiente virtual**

```bash
python -m venv .venv
source .venv/bin/activate  # no Windows: .venv\Scripts\activate
```

3. **Instalar dependências**

```bash
pip install -r requirements.txt
```

4. **Configurar variáveis de ambiente**

```bash
cp .env.example .env
# Editar .env e adicionar sua chave OpenAI
```

5. **Iniciar o servidor MCP** (em outro terminal)

```bash
cd ../Servidor\ MCP\ \(Compartilhado\)
TEMA=equipamentos python mundo.py
```

6. **Executar o time de agentes**

```bash
python main.py
```

## Uso

### Execução básica

```bash
python main.py
```

### Opções

```bash
python main.py --help
```

- `--mcp-url`: URL do servidor MCP (padrão: `http://localhost:8765/mcp`)
- `--max-eventos`: Máximo de eventos a processar
- `--checkpoint-dir`: Diretório para checkpoints SQLite

### Exemplos

```bash
# Processar até 10 eventos
python main.py --max-eventos 10

# Usar servidor MCP em outro host
python main.py --mcp-url http://192.168.1.100:8765/mcp
```

## Fluxo de Processamento

### 1. Coordenador
- Chama `proximo_evento` em laço
- Detecta virada de dia (tick diário)
- Roteia para Analista

### 2. Analista
- Classifica tipo de evento com LLM
- Extrai entidades (patrimonio, colaborador, data, etc)
- Consulta MCP para resolver dados
- Monta plano de ações

### 3. Revisor
- Valida regras de negócio
- Atribui nível final (FAZ_SOZINHO, PROPÕE, ESCALA)
- Detecta bloqueios (e-mail externo, duplicidade)

### 4. Executor
- Executa ações do plano aprovado
- Atualiza inventário
- Responde eventos
- Envia mensagens

## Tipos de Eventos

| Tipo | Ações | Nível |
|---|---|---|
| `duvida` | Responder com template | FAZ |
| `consulta_estoque` | Consultar e responder | FAZ |
| `devolucao` | Atualizar status, responder | FAZ |
| `alocacao` / `reserva_kit` | Reservar, responder | FAZ/PROPÕE |
| `troca_defeito` | Marcar danificado, responder | FAZ |
| `emprestimo` | Registrar empréstimo | PROPÕE |
| `entrada_pessoa` | Preparar kit | FAZ/PROPÕE |
| `saida_pessoa` | Cobrar devolução | FAZ |
| `baixa` | Baixar item | ESCALA |
| `entrega_compra` | Atualizar pendências | FAZ |

## Regras de Negócio

- **Limite de compra autônoma**: R$ 500
- **Dias para cobrança**: 5 dias úteis
- **Dias para escalar**: 10 dias úteis
- **Estoque mínimo**: 3 itens

## Resiliência

### Conexão MCP

O cliente usa o protocolo MCP Streamable HTTP em `--mcp-url`: abre uma sessão
(`initialize`), envia `notifications/initialized` e chama as ferramentas
JSON-RPC do servidor. Respostas JSON e SSE são aceitas. O agente é identificado
como `orquestrador`; para testar a conexão sem iniciar o grafo, use:

```bash
python -c "from src.mcp_client import MCPClient; c=MCPClient(); c.initialize(); print(c.listar_bases()); c.close()"
```

O servidor disponibiliza operações genéricas como `consultar`, `atualizar`,
`registrar` e `responder_evento`. Ações da aplicação sem uma operação equivalente
no servidor são reportadas como erro, em vez de serem tratadas como sucesso.

### Retry
- 503 Service Unavailable: retry com backoff exponencial (0.5s, 1s, 2s)
- Máximo 4 tentativas

### Idempotência
- Hash de `evento_id + tool + args`
- Cache em memória
- Verificação antes de repetir (504)

### Circuit Breaker
- 5 falhas consecutivas: pausa 3s
- Eventos preservados no checkpoint

## Logging

Logs são salvos em `agentes.log` e exibidos no console.

```
2026-01-05 10:30:45 - src.agents.coordenador - INFO - Coordenador iniciado
2026-01-05 10:30:46 - src.agents.analista - INFO - Analista processando evento EVT-001
...
```

## Testes

```bash
# Executar testes
pytest tests/

# Com cobertura
pytest --cov=src tests/
```

## Desenvolvimento

### Adicionar novo tipo de evento

1. Adicionar tipo em `rules.py` → `TIPOS_EVENTO`
2. Adicionar lógica em `analista.py` → `_montar_plano()`
3. Adicionar validação em `revisor.py` → `_validar_acao()`
4. Adicionar execução em `executor.py` → `_executar_acao()`

### Adicionar nova regra

1. Implementar em `rules.py`
2. Chamar em `revisor.py` → `_validar_acao()`

## Troubleshooting

### Erro: "Connection refused"
- Verificar se servidor MCP está rodando
- Verificar URL em `--mcp-url`

### Erro: "OPENAI_API_KEY not found"
- Criar arquivo `.env` com chave da API
- Ou exportar variável: `export OPENAI_API_KEY=sk-...`

### Erro: "504 Gateway Timeout"
- Servidor MCP pode estar sobrecarregado
- Aumentar `--segundos-por-dia` no servidor

## Métricas

Ao final da execução:
- Eventos processados
- Tokens LLM usados
- Erros encontrados

## Licença

Hackathon UNIFEI 2026

## Contato

Time de Gestão de Equipamentos
