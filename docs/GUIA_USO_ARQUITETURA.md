# Guia de Uso — Arquitetura Simplificada

## Como Usar o Grafo

### 1. Importar e Criar o Grafo

```python
from src.graph import criar_grafo
from src.mcp_client import MCPClient
from src.llm import LLMClient
from src.clock import Clock
from src.rules import RegrasEquipamentos

# Criar instâncias
mcp = MCPClient(base_url="http://localhost:8765/mcp")
llm = LLMClient(api_key="sk-...")
clock = Clock()
regras = RegrasEquipamentos(cache={})

# Criar grafo
graph = criar_grafo(mcp, llm, clock, regras)
```

### 2. Invocar o Grafo

```python
from src.state import AgentState

# Estado inicial
initial_state = AgentState(
    evento_id="",
    evento={},
    encerrado=False,
    erros=[],
    cache={},
    pendencias={},
)

# Invocar grafo
result = graph.invoke(initial_state)

# Acessar resultado
print(f"Evento ID: {result['evento_id']}")
print(f"Tipo: {result['tipo']}")
print(f"Aprovado: {result['aprovado']}")
print(f"Resposta: {result['resposta_remetente']}")
```

### 3. Com Checkpointing

```python
# Criar grafo com checkpoint
graph = criar_grafo(
    mcp, llm, clock, regras,
    checkpoint_dir=".checkpoints"
)

# Invocar com thread_id para persistência
result = graph.invoke(
    initial_state,
    config={"configurable": {"thread_id": "evento-001"}}
)

# Recuperar estado anterior
result = graph.invoke(
    initial_state,
    config={"configurable": {"thread_id": "evento-001"}}
)
```

---

## Estrutura de Cada Nó

### Padrão de Implementação

```python
"""
Nó X: [Nome] — [Descrição].
"""

import logging
from ..state import AgentState
from ..dependencies import Dependency

logger = logging.getLogger(__name__)

def node(state: AgentState, dependency: Dependency) -> AgentState:
    """
    [Descrição clara da responsabilidade].
    
    Entrada: [campos do estado]
    Saída: [campos modificados]
    """
    
    # Validar entrada
    if not state.get("required_field"):
        logger.warning("Campo obrigatório ausente")
        return state
    
    logger.info(f"Processando {state['evento_id']}")
    
    try:
        # Lógica principal
        result = dependency.do_something(state["data"])
        state["output_field"] = result
        
        logger.info("Sucesso")
        return state
    
    except Exception as e:
        logger.error(f"Erro: {e}")
        state["erros"].append(str(e))
        return state
```

---

## Adicionar um Novo Nó

### 1. Criar Arquivo

```bash
touch src/nodes/novo_no.py
```

### 2. Implementar Nó

```python
"""
Nó X: Novo Nó — Descrição.
"""

import logging
from ..state import AgentState

logger = logging.getLogger(__name__)

def node(state: AgentState) -> AgentState:
    """Descrição clara."""
    logger.info(f"Processando {state['evento_id']}...")
    
    try:
        # Lógica
        state["novo_campo"] = "valor"
        return state
    except Exception as e:
        logger.error(f"Erro: {e}")
        state["erros"].append(str(e))
        return state
```

### 3. Adicionar ao Grafo

```python
# Em src/graph.py

from .nodes import novo_no

# Adicionar nó
workflow.add_node("novo_no", lambda s: novo_no.node(s))

# Adicionar transição
workflow.add_edge("nó_anterior", "novo_no")
workflow.add_edge("novo_no", "nó_próximo")
```

### 4. Testar Nó

```python
# Em tests/test_nodes.py

def test_novo_no(base_state, mocks):
    """Testa novo nó."""
    result = novo_no.node(base_state)
    assert result["novo_campo"] == "valor"
```

---

## Modificar um Nó Existente

### 1. Editar Arquivo

```bash
vim src/nodes/classificar.py
```

### 2. Testar Mudanças

```bash
pytest tests/test_nodes.py::test_classificar_evento_valido -v
```

### 3. Rodar Todos os Testes

```bash
pytest tests/ -v
```

---

## Debugging

### 1. Ativar Logs Detalhados

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("src")
logger.setLevel(logging.DEBUG)

# Invocar grafo
result = graph.invoke(initial_state)
```

### 2. Inspecionar Estado

```python
# Após cada nó
print(f"Estado após classificar:")
print(f"  tipo: {result['tipo']}")
print(f"  confianca: {result['confianca']}")
print(f"  entidades: {result['entidades']}")
```

### 3. Verificar Erros

```python
if result.get("erros"):
    print("Erros encontrados:")
    for erro in result["erros"]:
        print(f"  - {erro}")
```

---

## Testes

### Rodar Todos os Testes

```bash
pytest tests/ -v
```

### Rodar Testes de um Nó

```bash
pytest tests/test_nodes.py::test_classificar_evento_valido -v
```

### Rodar com Cobertura

```bash
pytest tests/ --cov=src --cov-report=html
```

---

## Fluxo Condicional

### Exemplo: Após Aguardar Evento

```python
def deve_classificar(state: AgentState) -> str:
    """Após aguardar evento: classificar ou encerrar."""
    if state.get("encerrado"):
        return END
    if state.get("evento"):
        return "classificar"
    return "aguardar_evento"

workflow.add_conditional_edges("aguardar_evento", deve_classificar)
```

### Exemplo: Após Aprovar

```python
def deve_executar(state: AgentState) -> str:
    """Após aprovar: executar se aprovado, senão voltar."""
    if state.get("aprovado"):
        return "executar"
    return "aguardar_evento"

workflow.add_conditional_edges("aprovar", deve_executar)
```

---

## Tratamento de Erros

### Padrão de Erro

```python
try:
    # Lógica
    result = dependency.do_something()
    state["field"] = result
except SpecificError as e:
    logger.warning(f"Erro esperado: {e}")
    state["fallback"] = True
except Exception as e:
    logger.error(f"Erro inesperado: {e}")
    state["erros"].append(str(e))

return state
```

### Recuperação de Erro

```python
# Nó anterior detecta erro
if state.get("erros"):
    # Voltar ao início ou nó anterior
    return "aguardar_evento"
```

---

## Performance

### Otimizações

1. **Cache**: Armazenar resultados em `state["cache"]`
2. **Retry**: Adicionar retry em nós críticos
3. **Timeout**: Definir timeout em chamadas MCP/LLM
4. **Paralelo**: Nós independentes podem rodar em paralelo

### Exemplo: Cache

```python
def node(state: AgentState, mcp: MCPClient) -> AgentState:
    """Usa cache para evitar chamadas repetidas."""
    
    cache = state.get("cache", {})
    
    # Verificar cache
    if "inventario" in cache:
        state["entidades"]["item_atual"] = cache["inventario"]
        return state
    
    # Chamar MCP
    inv = mcp.consultar_inventario(...)
    
    # Armazenar em cache
    cache["inventario"] = inv
    state["cache"] = cache
    
    return state
```

---

## Monitoramento

### Logs Importantes

```python
logger.info(f"Evento {state['evento_id']}: iniciado")
logger.info(f"Tipo: {state['tipo']}, Confiança: {state['confianca']:.2f}")
logger.info(f"Plano: {len(state['plano'])} ações")
logger.info(f"Aprovado: {state['aprovado']}")
logger.info(f"Executadas: {len(state['acoes_feitas'])} ações")
```

### Métricas

```python
# Tempo de execução
import time
start = time.time()
result = graph.invoke(initial_state)
elapsed = time.time() - start
print(f"Tempo: {elapsed:.2f}s")

# Tokens usados
tokens = sum(a.get("tokens", 0) for a in result.get("acoes_feitas", []))
print(f"Tokens: {tokens}")
```

---

## Troubleshooting

### Problema: Nó não é executado

**Solução**: Verificar transições condicionais

```python
# Verificar se a condição é verdadeira
if state.get("evento"):
    print("Evento presente, deve classificar")
else:
    print("Sem evento, volta ao aguardar")
```

### Problema: Estado não é atualizado

**Solução**: Garantir que o nó retorna o estado modificado

```python
def node(state: AgentState) -> AgentState:
    state["field"] = "value"  # Modificar
    return state  # Retornar
```

### Problema: Erro em nó específico

**Solução**: Adicionar try/except e logging

```python
try:
    result = dependency.do_something()
except Exception as e:
    logger.error(f"Erro em {state['evento_id']}: {e}")
    state["erros"].append(str(e))
```

---

## Próximos Passos

1. Implementar novos nós conforme necessário
2. Adicionar testes para cada nó
3. Monitorar performance em produção
4. Otimizar com cache e retry
5. Documentar mudanças

---

## Referências

- [docs/ARQUITETURA_SIMPLIFICADA.md](ARQUITETURA_SIMPLIFICADA.md)
- [docs/IMPLEMENTACAO_CONCLUIDA.md](IMPLEMENTACAO_CONCLUIDA.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
