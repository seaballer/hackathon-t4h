# Arquitetura Simplificada — Um Agente, Múltiplos Nós

Repensamento completo da arquitetura: **um único agente com cada ação como um nó no grafo LangGraph**.

---

## 1. Conceito

### Antes (Atual)
```
4 Agentes (Coordenador, Analista, Revisor, Executor)
↓
Cada agente é um nó no grafo
↓
Cada agente faz múltiplas responsabilidades
```

### Depois (Proposto)
```
1 Agente (Colaborador Digital)
↓
Cada ação é um nó no grafo
↓
Cada nó faz UMA coisa bem definida
```

---

## 2. Novo Fluxo

### Nós do Grafo

```
[Início]
   ↓
[1. Aguardar Evento] ← Chamar proximo_evento()
   ↓
[2. Classificar] ← LLM: tipo + entidades
   ↓
[3. Resolver Dados] ← Consultar MCP (inventário, etc)
   ↓
[4. Montar Plano] ← Criar lista de ações
   ↓
[5. Validar] ← Verificar regras de negócio
   ↓
[6. Aprovar] ← Decidir se executa (FAZ/PROPÕE/ESCALA)
   ↓
[7. Executar] ← Chamar MCP tools
   ↓
[8. Registrar] ← Salvar resultado
   ↓
[9. Responder] ← Enviar resposta ao remetente
   ↓
[Volta ao 1]
```

### Cada Nó é Independente

```python
# Nó 1: Aguardar Evento
def node_aguardar_evento(state):
    resposta = mcp.proximo_evento(esperar_segundos=30)
    state["evento"] = resposta.get("evento")
    state["encerrado"] = resposta.get("encerrado")
    return state

# Nó 2: Classificar
def node_classificar(state):
    tipo, confianca, entidades = llm.classificar_evento(state["evento"])
    state["tipo"] = tipo
    state["entidades"] = entidades
    return state

# Nó 3: Resolver Dados
def node_resolver_dados(state):
    if state["entidades"].get("patrimonio"):
        inv = mcp.consultar_inventario(...)
        state["entidades"]["item_atual"] = inv
    return state

# ... e assim por diante
```

---

## 3. Vantagens da Nova Arquitetura

### ✅ Simplicidade
- Um agente, não 4
- Cada nó faz uma coisa
- Fácil de entender e debugar

### ✅ Testabilidade
- Cada nó pode ser testado isoladamente
- Sem dependências entre agentes
- Testes mais simples

### ✅ Manutenibilidade
- Mudança em um nó não afeta outros
- Fácil adicionar/remover nós
- Código mais limpo

### ✅ Observabilidade
- Cada nó é um ponto de observação
- Logs claros de cada etapa
- Fácil rastrear fluxo

### ✅ Escalabilidade
- Nós podem rodar em paralelo (com cuidado)
- Fácil adicionar cache entre nós
- Fácil adicionar retry por nó

---

## 4. Estado Único

Um único `AgentState` que flui por todos os nós:

```python
class AgentState(TypedDict, total=False):
    # Evento
    evento_id: str
    evento: Dict[str, Any]
    encerrado: bool
    
    # Classificação
    tipo: str
    confianca: float
    
    # Entidades
    entidades: Dict[str, Any]
    
    # Plano
    plano: List[Dict[str, Any]]
    
    # Validação
    bloqueios: List[str]
    aprovado: bool
    
    # Execução
    acoes_feitas: List[Dict[str, Any]]
    resposta_remetente: str
    
    # Contexto
    cache: Dict[str, Any]
    erros: List[str]
```

---

## 5. Fluxo Condicional

### Decisões Simples

```python
# Após Aguardar Evento
def deve_classificar(state):
    if state.get("encerrado"):
        return "fim"
    if state.get("evento"):
        return "classificar"
    return "aguardar_evento"  # Volta ao início

# Após Validar
def deve_executar(state):
    if state.get("aprovado"):
        return "executar"
    return "aguardar_evento"  # Volta ao início

# Após Executar
def deve_responder(state):
    if state.get("acoes_feitas"):
        return "responder"
    return "aguardar_evento"
```

---

## 6. Comparação: Antes vs. Depois

### Antes (4 Agentes)

| Aspecto | Valor |
|---------|-------|
| Agentes | 4 |
| Nós no grafo | 4 |
| Responsabilidades por agente | 3-4 |
| Linhas de código | ~1.280 |
| Complexidade | Alta |
| Testabilidade | Média |

### Depois (1 Agente)

| Aspecto | Valor |
|---------|-------|
| Agentes | 1 |
| Nós no grafo | 9 |
| Responsabilidades por nó | 1 |
| Linhas de código | ~1.200 |
| Complexidade | Baixa |
| Testabilidade | Alta |

---

## 7. Estrutura de Arquivos

```
src/
├── __init__.py
├── state.py                    # AgentState único
├── graph.py                    # Grafo com 9 nós
├── nodes/                      # Cada nó é um arquivo
│   ├── __init__.py
│   ├── aguardar_evento.py      # Nó 1
│   ├── classificar.py          # Nó 2
│   ├── resolver_dados.py       # Nó 3
│   ├── montar_plano.py         # Nó 4
│   ├── validar.py              # Nó 5
│   ├── aprovar.py              # Nó 6
│   ├── executar.py             # Nó 7
│   ├── registrar.py            # Nó 8
│   └── responder.py            # Nó 9
├── mcp_client.py               # Cliente MCP
├── llm.py                      # Cliente LLM
├── clock.py                    # Relógio
└── rules.py                    # Regras de negócio
```

---

## 8. Exemplo: Nó Simples

```python
# src/nodes/classificar.py

import logging
from typing import Dict, Any
from ..llm import LLMClient
from ..state import AgentState

logger = logging.getLogger(__name__)

def classificar(state: AgentState, llm: LLMClient) -> AgentState:
    """Classifica o evento com LLM."""
    
    if not state.get("evento"):
        logger.warning("Sem evento para classificar")
        return state
    
    logger.info(f"Classificando evento {state['evento_id']}")
    
    try:
        tipo, confianca, entidades = llm.classificar_evento(
            state["evento"],
            state.get("cache", {}).get("regras", {})
        )
        
        state["tipo"] = tipo
        state["confianca"] = confianca
        state["entidades"] = entidades
        
        logger.info(f"Tipo: {tipo}, Confiança: {confianca}")
        
        # Reanalizar se confiança baixa
        if confianca < 0.7:
            logger.warning(f"Confiança baixa ({confianca}), reanalisa ndo...")
            tipo, confianca, entidades = llm.reanalizar_evento(
                state["evento"],
                f"Confiança inicial baixa ({confianca})"
            )
            state["tipo"] = tipo
            state["confianca"] = confianca
            state["entidades"] = entidades
        
        return state
    
    except Exception as e:
        logger.error(f"Erro ao classificar: {e}")
        state["erros"].append(str(e))
        state["tipo"] = "outro"
        return state
```

---

## 9. Grafo Simplificado

```python
# src/graph.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .state import AgentState
from .nodes import (
    aguardar_evento, classificar, resolver_dados,
    montar_plano, validar, aprovar, executar,
    registrar, responder
)
from .mcp_client import MCPClient
from .llm import LLMClient
from .clock import Clock
from .rules import RegrasEquipamentos

def criar_grafo(mcp: MCPClient, llm: LLMClient, clock: Clock,
                regras: RegrasEquipamentos, checkpoint_dir: str = ".checkpoints"):
    """Cria o grafo com 9 nós."""
    
    workflow = StateGraph(AgentState)
    
    # Adicionar nós
    workflow.add_node("aguardar_evento", 
                     lambda s: aguardar_evento.node(s, mcp, clock))
    workflow.add_node("classificar", 
                     lambda s: classificar.node(s, llm))
    workflow.add_node("resolver_dados", 
                     lambda s: resolver_dados.node(s, mcp))
    workflow.add_node("montar_plano", 
                     lambda s: montar_plano.node(s, regras))
    workflow.add_node("validar", 
                     lambda s: validar.node(s, regras))
    workflow.add_node("aprovar", 
                     lambda s: aprovar.node(s))
    workflow.add_node("executar", 
                     lambda s: executar.node(s, mcp, llm))
    workflow.add_node("registrar", 
                     lambda s: registrar.node(s))
    workflow.add_node("responder", 
                     lambda s: responder.node(s, llm, mcp))
    
    # Definir fluxo
    workflow.set_entry_point("aguardar_evento")
    
    # Transições
    workflow.add_conditional_edges("aguardar_evento", 
                                   lambda s: "classificar" if s.get("evento") else 
                                            "fim" if s.get("encerrado") else 
                                            "aguardar_evento")
    
    workflow.add_edge("classificar", "resolver_dados")
    workflow.add_edge("resolver_dados", "montar_plano")
    workflow.add_edge("montar_plano", "validar")
    workflow.add_edge("validar", "aprovar")
    
    workflow.add_conditional_edges("aprovar",
                                   lambda s: "executar" if s.get("aprovado") else 
                                            "aguardar_evento")
    
    workflow.add_edge("executar", "registrar")
    workflow.add_edge("registrar", "responder")
    workflow.add_edge("responder", "aguardar_evento")
    
    workflow.add_edge("fim", END)
    
    # Compilar
    checkpointer = SqliteSaver(checkpoint_dir)
    graph = workflow.compile(checkpointer=checkpointer)
    
    return graph
```

---

## 10. Benefícios Práticos

### Para Desenvolvimento
- Cada nó é um arquivo separado
- Fácil encontrar código específico
- Fácil adicionar novo nó

### Para Testes
- Cada nó pode ser testado isoladamente
- Fixtures simples (apenas state)
- Testes mais rápidos

### Para Debugging
- Logs claros de cada etapa
- Fácil pausar em nó específico
- Fácil inspecionar state

### Para Produção
- Fácil adicionar retry por nó
- Fácil adicionar cache entre nós
- Fácil monitorar performance de cada nó

---

## 11. Checklist de Implementação

- [ ] Criar `src/nodes/` diretório
- [ ] Criar 9 arquivos de nó
- [ ] Atualizar `src/state.py`
- [ ] Reescrever `src/graph.py`
- [ ] Remover `src/agents/` diretório
- [ ] Atualizar testes
- [ ] Atualizar documentação
- [ ] Testar fluxo completo

---

## 12. Conclusão

A nova arquitetura é **muito mais simples e clara**:
- 1 agente em vez de 4
- 9 nós simples em vez de 4 agentes complexos
- Cada nó faz uma coisa bem definida
- Fácil de entender, testar e manter

**Recomendação**: Implementar esta arquitetura simplificada.
