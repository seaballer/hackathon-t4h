# Plano de Implementação — Arquitetura Simplificada

Guia passo-a-passo para implementar a nova arquitetura com 1 agente e 9 nós.

---

## 1. Fase 1: Preparação (30 min)

### 1.1 Criar Branch
```bash
git checkout -b feature/arquitetura-simplificada
```

### 1.2 Criar Estrutura de Diretórios
```bash
mkdir -p src/nodes
touch src/nodes/__init__.py
```

### 1.3 Atualizar State
Arquivo: `src/state.py`

Adicionar campos:
```python
class AgentState(TypedDict, total=False):
    # ... campos existentes ...
    confianca: float  # Confiança da classificação
    aprovado: bool    # Se foi aprovado para execução
```

---

## 2. Fase 2: Criar Nós (2-3 horas)

### 2.1 Nó 1: Aguardar Evento
Arquivo: `src/nodes/aguardar_evento.py`

```python
def node(state: AgentState, mcp: MCPClient, clock: Clock) -> AgentState:
    """Aguarda próximo evento do MCP."""
    resposta = mcp.proximo_evento(esperar_segundos=30)
    
    if resposta.get("encerrado"):
        state["encerrado"] = True
        return state
    
    if resposta.get("evento"):
        state["evento_id"] = resposta["evento"]["id"]
        state["evento"] = resposta["evento"]
        state["data_simulada"] = resposta.get("agora", "")
    
    return state
```

### 2.2 Nó 2: Classificar
Arquivo: `src/nodes/classificar.py`

```python
def node(state: AgentState, llm: LLMClient) -> AgentState:
    """Classifica evento com LLM."""
    if not state.get("evento"):
        return state
    
    tipo, confianca, entidades = llm.classificar_evento(
        state["evento"],
        state.get("cache", {}).get("regras", {})
    )
    
    state["tipo"] = tipo
    state["confianca"] = confianca
    state["entidades"] = entidades
    
    # Reanalizar se confiança baixa
    if confianca < 0.7:
        tipo, confianca, entidades = llm.reanalizar_evento(
            state["evento"],
            f"Confiança inicial baixa ({confianca})"
        )
        state["tipo"] = tipo
        state["confianca"] = confianca
        state["entidades"] = entidades
    
    return state
```

### 2.3 Nó 3: Resolver Dados
Arquivo: `src/nodes/resolver_dados.py`

```python
def node(state: AgentState, mcp: MCPClient) -> AgentState:
    """Resolve entidades consultando MCP."""
    if state["entidades"].get("patrimonio"):
        try:
            inv = mcp.consultar_inventario({
                "patrimonio": state["entidades"]["patrimonio"]
            })
            if inv.get("itens"):
                state["entidades"]["item_atual"] = inv["itens"][0]
        except Exception as e:
            logger.warning(f"Erro ao consultar inventário: {e}")
    
    return state
```

### 2.4 Nó 4: Montar Plano
Arquivo: `src/nodes/montar_plano.py`

```python
def node(state: AgentState, regras: RegrasEquipamentos) -> AgentState:
    """Monta plano de ações baseado no tipo."""
    tipo = state.get("tipo", "outro")
    entidades = state.get("entidades", {})
    
    plano = []
    
    if tipo == "duvida":
        plano.append({
            "tool": "responder_evento",
            "args": {"evento_id": state["evento_id"]},
            "motivo": "Responder dúvida",
            "nivel": "FAZ_SOZINHO"
        })
    
    # ... mais tipos ...
    
    state["plano"] = plano
    return state
```

### 2.5 Nó 5: Validar
Arquivo: `src/nodes/validar.py`

```python
def node(state: AgentState, regras: RegrasEquipamentos) -> AgentState:
    """Valida plano contra regras."""
    bloqueios = []
    plano_valido = []
    
    for acao in state.get("plano", []):
        valida, motivo = _validar_acao(acao, state, regras)
        if not valida:
            bloqueios.append(f"{acao['tool']}: {motivo}")
        else:
            plano_valido.append(acao)
    
    state["plano"] = plano_valido
    state["bloqueios"] = bloqueios
    
    return state
```

### 2.6 Nó 6: Aprovar
Arquivo: `src/nodes/aprovar.py`

```python
def node(state: AgentState) -> AgentState:
    """Decide se aprova execução."""
    if state.get("bloqueios"):
        state["aprovado"] = False
    else:
        state["aprovado"] = True
    
    return state
```

### 2.7 Nó 7: Executar
Arquivo: `src/nodes/executar.py`

```python
def node(state: AgentState, mcp: MCPClient, llm: LLMClient) -> AgentState:
    """Executa ações do plano."""
    if not state.get("aprovado"):
        return state
    
    acoes_feitas = []
    
    for acao in state.get("plano", []):
        try:
            resultado = _executar_acao(acao, state, mcp, llm)
            acoes_feitas.append({
                "tool": acao["tool"],
                "resultado": resultado
            })
        except Exception as e:
            logger.error(f"Erro ao executar {acao['tool']}: {e}")
            state["erros"].append(str(e))
    
    state["acoes_feitas"] = acoes_feitas
    return state
```

### 2.8 Nó 8: Registrar
Arquivo: `src/nodes/registrar.py`

```python
def node(state: AgentState) -> AgentState:
    """Registra ações feitas."""
    logger.info(f"Evento {state['evento_id']}: {len(state.get('acoes_feitas', []))} ações executadas")
    return state
```

### 2.9 Nó 9: Responder
Arquivo: `src/nodes/responder.py`

```python
def node(state: AgentState, llm: LLMClient, mcp: MCPClient) -> AgentState:
    """Envia resposta ao remetente."""
    if not state.get("acoes_feitas"):
        return state
    
    try:
        resposta = llm.redigir_resposta(
            state.get("tipo", ""),
            state.get("entidades", {}),
            {"acoes": len(state["acoes_feitas"])}
        )
        state["resposta_remetente"] = resposta
    except Exception as e:
        logger.warning(f"Erro ao redigir resposta: {e}")
        state["resposta_remetente"] = "Sua solicitação foi processada."
    
    return state
```

---

## 3. Fase 3: Reescrever Grafo (1 hora)

Arquivo: `src/graph.py`

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .state import AgentState
from .nodes import (
    aguardar_evento, classificar, resolver_dados,
    montar_plano, validar, aprovar, executar,
    registrar, responder
)

def criar_grafo(mcp, llm, clock, regras, checkpoint_dir=".checkpoints"):
    """Cria grafo com 9 nós."""
    
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

## 4. Fase 4: Atualizar Testes (1-2 horas)

### 4.1 Testes de Nós
Arquivo: `tests/test_nodes.py`

```python
import pytest
from src.state import AgentState
from src.nodes import classificar, validar, aprovar

def test_classificar_evento_valido():
    """Testa classificação de evento válido."""
    state = AgentState(
        evento_id="PED-001",
        evento={"assunto": "Dúvida", "corpo": "..."}
    )
    # Mock LLM
    result = classificar.node(state, mock_llm)
    assert result["tipo"] == "duvida"

def test_validar_plano_com_bloqueios():
    """Testa validação com bloqueios."""
    state = AgentState(
        plano=[{"tool": "atualizar", "args": {"patrimonio": None}}]
    )
    result = validar.node(state, mock_regras)
    assert len(result["bloqueios"]) > 0

def test_aprovar_sem_bloqueios():
    """Testa aprovação sem bloqueios."""
    state = AgentState(bloqueios=[])
    result = aprovar.node(state)
    assert result["aprovado"] is True
```

---

## 5. Fase 5: Limpeza (30 min)

### 5.1 Remover Código Antigo
```bash
rm -rf src/agents/
```

### 5.2 Atualizar Imports
Arquivo: `src/__init__.py`

```python
from .graph import criar_grafo
from .state import AgentState

__all__ = ["criar_grafo", "AgentState"]
```

### 5.3 Atualizar main.py
Arquivo: `main.py`

```python
from src.graph import criar_grafo
from src.mcp_client import MCPClient
from src.llm import LLMClient
from src.clock import Clock
from src.rules import RegrasEquipamentos

# ... setup ...

graph = criar_grafo(mcp, llm, clock, regras)
graph.invoke({"cache": {...}, "pendencias": {...}})
```

---

## 6. Fase 6: Documentação (30 min)

- [ ] Atualizar `docs/AGENTES.md` → `docs/NOS.md`
- [ ] Atualizar `docs/ARQUITETURA.md`
- [ ] Criar `docs/GUIA_ADICIONAR_NO.md`
- [ ] Atualizar `README.md`

---

## 7. Timeline Total

| Fase | Tempo | Status |
|------|-------|--------|
| 1. Preparação | 30 min | ⏳ |
| 2. Criar Nós | 2-3h | ⏳ |
| 3. Reescrever Grafo | 1h | ⏳ |
| 4. Atualizar Testes | 1-2h | ⏳ |
| 5. Limpeza | 30 min | ⏳ |
| 6. Documentação | 30 min | ⏳ |
| **Total** | **6-8h** | ⏳ |

---

## 8. Checklist de Implementação

- [ ] Branch criado: `feature/arquitetura-simplificada`
- [ ] Diretório `src/nodes/` criado
- [ ] 9 nós implementados
- [ ] `src/state.py` atualizado
- [ ] `src/graph.py` reescrito
- [ ] `src/agents/` removido
- [ ] Testes atualizados
- [ ] Testes passando: `pytest tests/ -v`
- [ ] Documentação atualizada
- [ ] Commit: `git commit -m "refactor: arquitetura simplificada com 9 nós"`
- [ ] PR criado para `main`

---

## 9. Rollback

Se precisar reverter:

```bash
git checkout main
git branch -D feature/arquitetura-simplificada
```

---

## 10. Próximos Passos

1. Implementar as 6 fases
2. Testar fluxo completo
3. Fazer PR para revisão
4. Merge para `main`
5. Deploy
