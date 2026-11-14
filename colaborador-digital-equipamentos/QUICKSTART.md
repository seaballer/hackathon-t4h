# Quick Start — Colaborador Digital

Guia rápido para começar em 5 minutos.

## 1. Preparar Ambiente (2 min)

```bash
# Entrar no diretório
cd colaborador-digital-equipamentos

# Criar ambiente virtual
python -m venv .venv

# Ativar (escolha seu SO)
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

## 2. Configurar Chave OpenAI (1 min)

```bash
# Copiar exemplo
cp .env.example .env

# Editar .env e adicionar sua chave
# OPENAI_API_KEY=sk-...
```

## 3. Iniciar Servidor MCP (1 min)

Em **outro terminal**:

```bash
cd "Servidor MCP (Compartilhado)"

# Windows:
$env:TEMA="equipamentos"
python mundo.py

# macOS/Linux:
TEMA=equipamentos python mundo.py
```

Aguarde até ver:
```
Painel ao vivo: http://localhost:8765
Servidor MCP: http://localhost:8765/mcp
```

## 4. Executar Agentes (1 min)

De volta ao **primeiro terminal**:

```bash
python main.py
```

Você verá:
```
2026-01-05 10:30:45 - src.agents.coordenador - INFO - Coordenador iniciado
2026-01-05 10:30:46 - src.agents.coordenador - INFO - Aguardando próximo evento...
...
```

## 5. Monitorar Execução

### Logs em tempo real
```bash
tail -f agentes.log
```

### Painel ao vivo
Abra no navegador: http://localhost:8765

### Parar execução
Pressione `Ctrl+C` em qualquer terminal

---

## Próximos Passos

### Rodar Testes
```bash
pytest tests/ -v
```

### Processar Limite de Eventos
```bash
python main.py --max-eventos 10
```

### Usar Servidor MCP em Outro Host
```bash
python main.py --mcp-url http://192.168.1.100:8765/mcp
```

---

## Troubleshooting Rápido

| Erro | Solução |
|---|---|
| `Connection refused` | Verificar se servidor MCP está rodando |
| `OPENAI_API_KEY not found` | Editar `.env` com sua chave |
| `ModuleNotFoundError` | Rodar `pip install -r requirements.txt` |
| `504 Gateway Timeout` | Servidor MCP sobrecarregado, aguarde |

---

## Estrutura Mínima

```
colaborador-digital-equipamentos/
├── src/                    # Código dos agentes
├── tests/                  # Testes
├── main.py                 # Ponto de entrada
├── requirements.txt        # Dependências
├── .env                    # Variáveis (criar a partir de .env.example)
└── README.md              # Documentação completa
```

---

## Arquivos Importantes

- **`main.py`**: Ponto de entrada — execute aqui
- **`src/graph.py`**: Orquestração dos agentes
- **`src/agents/`**: Os 4 agentes (coordenador, analista, revisor, executor)
- **`agentes.log`**: Log de execução
- **`.env`**: Suas variáveis de ambiente (criar a partir de `.env.example`)

---

## Tempo Estimado

- Instalação: 2 min
- Configuração: 1 min
- Servidor MCP: 1 min
- Execução: 1 min
- **Total: 5 min** ✅

---

## Próxima Leitura

Depois de rodar com sucesso, leia:
1. `README.md` — Documentação completa
2. `IMPLEMENTACAO.md` — O que foi implementado
3. `ESTRUTURA.txt` — Visão geral do projeto

---

**Pronto? Comece agora!** 🚀
