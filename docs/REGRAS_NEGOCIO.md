# Regras de Negócio — Gestão de Equipamentos

Documento detalhado das regras de negócio implementadas no sistema de gestão de equipamentos de TI.

---

## 1. Limites de Autonomia

O sistema tem **3 níveis de decisão** que determinam se uma ação é executada automaticamente ou precisa de aprovação:

### FAZ_SOZINHO (Executa imediatamente)

Ações que o agente pode fazer sem aprovação:

- **Dúvidas**: responder perguntas simples
- **Consulta de estoque**: informar disponibilidade
- **Devoluções**: aceitar item devolvido
- **Respostas a cobranças**: confirmar recebimento
- **Trocas de defeito**: substituir item danificado
- **Entrega de compra**: registrar chegada
- **Alocações/Reservas**: quando há estoque disponível
- **Entrada de pessoa**: preparar kit padrão

### PROPÕE (Requer aprovação)

Ações que precisam de validação antes de executar:

- **Alocação/Reserva**: quando **não há estoque** E valor ≤ R$ 500
- **Entrada de pessoa**: quando **não há estoque** E valor ≤ R$ 500
- **Empréstimo**: qualquer empréstimo (sempre requer aprovação)
- **Compra**: quando valor ≤ R$ 500

### ESCALA (Requer escalação para supervisor)

Ações críticas que precisam de decisão humana:

- **Baixa de item**: marcar como perdido/quebrado/danificado
- **Alocação/Reserva**: quando valor > R$ 500
- **Entrada de pessoa**: quando valor > R$ 500
- **Compra**: quando valor > R$ 500
- **Eventos desconhecidos**: tipo não classificado
- **Bloqueios**: e-mail externo, dados inválidos, etc.

#### Exemplo prático

```
Evento: "Preciso de um notebook para projeto"
Valor do notebook: R$ 4.800

Análise:
- Tipo: alocacao
- Valor: 4.800 > 500
- Nível: ESCALA ← Precisa de aprovação!

Resultado: Não executa automaticamente, envia para supervisor
```

---

## 2. Limites Financeiros

### Limite de Compra Autônoma: R$ 500

| Valor | Nível | Ação |
|-------|-------|------|
| ≤ R$ 500 | PROPÕE | Pode ser aprovado por supervisor |
| > R$ 500 | ESCALA | Requer escalação para alçada superior |

### Catálogo de preços

- **Notebook**: R$ 4.800 (10 dias úteis) → ESCALA
- **Monitor**: R$ 890 (7 dias úteis) → ESCALA
- **Headset**: R$ 320 (3 dias úteis) → PROPÕE
- **Kit teclado e mouse**: R$ 180 (3 dias úteis) → PROPÕE
- **Carregador**: R$ 260 (5 dias úteis) → PROPÕE

---

## 3. Prazos e Datas

### Devolução após Saída

Quando alguém sai da empresa, há prazos para devolver os equipamentos:

| Dias úteis | Ação | Nível |
|-----------|------|-------|
| 0–5 dias | Não cobrar | FAZ_SOZINHO |
| 5–10 dias | Cobrar (enviar mensagem) | FAZ_SOZINHO |
| > 10 dias | Escalar para supervisor | ESCALA |

#### Exemplo

```
Evento: "Saída do André" (01/12)
Prazo de devolução: 5 dias úteis = 08/12

- 08/12: Não cobrar ainda
- 11/12: Cobrar (5º dia útil)
- 18/12: Escalar (10º dia útil)
```

### Empréstimo Máximo: 7 dias úteis

Empréstimos só podem ser por até 7 dias úteis. Acima disso, rejeitar.

```python
if dias_emprestimo > 7:
    return False, "Empréstimo máximo é 7 dias úteis"
```

### Kit Pronto 2 Dias Úteis Antes

Quando alguém entra, o kit deve estar pronto 2 dias úteis antes da data de entrada.

#### Exemplo

```
Entrada: 08/12 (segunda)
Kit pronto até: 06/12 (sexta anterior)
```

---

## 4. Estoque Mínimo

### Mínimo de 3 Itens Livres por Tipo

O sistema deve manter pelo menos 3 itens disponíveis de cada tipo:

| Tipo | Mínimo | Ação se < 3 |
|------|--------|------------|
| Notebook | 3 | Alertar e considerar compra |
| Monitor | 3 | Alertar e considerar compra |
| Headset | 3 | Alertar e considerar compra |
| Kit teclado e mouse | 3 | Alertar e considerar compra |
| Carregador | 3 | Alertar e considerar compra |

### Distribuição inicial (150 itens)

- 47 notebooks (113 alocados, 6 livres)
- 35 kits teclado e mouse (28 alocados, 4 livres)
- 34 headsets (27 alocados, 4 livres)
- 29 monitores (23 alocados, 1 livre)
- 5 carregadores (4 alocados, 2 livres)

---

## 5. Tipos de Eventos (12 Categorias)

O LLM classifica cada evento em um dos 12 tipos:

| Tipo | Descrição | Nível padrão | Exemplo |
|------|-----------|--------------|---------|
| `duvida` | Pergunta simples | FAZ_SOZINHO | "Qual o prazo de devolução?" |
| `consulta_estoque` | Consultar disponibilidade | FAZ_SOZINHO | "Quantos notebooks temos?" |
| `devolucao` | Retorno físico de item | FAZ_SOZINHO | "Estou devolvendo o notebook" |
| `resposta_cobranca` | Resposta a cobrança | FAZ_SOZINHO | "Vou devolver em breve" |
| `alocacao` | Alocar item para pessoa | FAZ_SOZINHO/PROPÕE/ESCALA | "Preciso de um notebook" |
| `reserva_kit` | Reservar kit para entrada | FAZ_SOZINHO/PROPÕE/ESCALA | "Kit para novo funcionário" |
| `troca_defeito` | Trocar item com defeito | FAZ_SOZINHO | "Meu headset não funciona" |
| `emprestimo` | Empréstimo temporário | PROPÕE | "Posso pegar emprestado?" |
| `entrada_pessoa` | Preparar kit para entrada | FAZ_SOZINHO/PROPÕE/ESCALA | "Novo funcionário entra dia X" |
| `saida_pessoa` | Desligamento e devolução | FAZ_SOZINHO | "Fulano está saindo" |
| `baixa` | Marcar como perdido/quebrado | ESCALA | "Perdi o headset" |
| `entrega_compra` | Compra chegou | FAZ_SOZINHO | "Notebook entregue" |
| `outro` | Desconhecido | ESCALA | Qualquer coisa fora dos 12 |

---

## 6. Status de Inventário (Máquina de Estados)

Cada item passa por estados bem definidos:

```
disponível ──→ reservado ──→ alocado ──→ disponível (devolução)
    ↓                            ↓
uso_interno                   baixado (perdido/quebrado)
    ↓                            ↓
  reservado/alocado          [FIM]
```

### Estados Válidos

- **disponível**: pronto para usar
- **reservado**: reservado para alguém (ainda não entrou)
- **alocado**: em uso por alguém
- **uso_interno**: equipamento da empresa (não alocado)
- **baixado**: perdido, quebrado ou danificado (definitivo)

### Transições Permitidas

| De | Para | Pré-condição | Erro |
|----|------|--------------|------|
| disponível | reservado/alocado | pessoa existe, não saiu | 422, 404 |
| reservado | alocado | mesmo dono | — |
| alocado | disponível | devolução física comprovada | 409 |
| alocado | baixado | situação = perdido/quebrado/danificado | 422 |
| qualquer | baixado | baixa definitiva | — |
| baixado | qualquer | NÃO PERMITIDO | 409 |

#### Exemplo de fluxo

```
1. Compra entregue → disponível (novo)
2. Reserva para entrada → reservado (com_quem = C-037)
3. Pessoa entra → alocado (com_quem = C-037)
4. Pessoa devolve → disponível (com_quem limpo)
5. Pessoa perde → baixado (situacao = perdido)
```

---

## 7. Validações de Segurança

### Bloqueio de E-mail Externo

```python
if origem == "email_externo":
    bloqueios.append("Evento de e-mail externo bloqueado por segurança")
    nivel_final = "ESCALA"
```

Qualquer evento vindo de fora do domínio `@t4h.exemplo` é bloqueado automaticamente.

### Validação de Pessoa

```python
if pessoa_saiu(data_saida):
    return False, "Pessoa já saiu da empresa"
```

Não é possível alocar item para alguém que já saiu.

### Validação de Item Usável

```python
if situacao not in ["novo", "usado"]:
    return False, "Item não é usável"
```

Só é possível alocar itens em condição `novo` ou `usado`. Itens `quebrado`, `danificado` ou `perdido` não podem ser alocados.

### Detecção de Duplicidade

```python
if evento_id in eventos_recentes:
    bloqueios.append("Evento duplicado detectado")
```

Se o mesmo evento chegar duas vezes, a segunda ocorrência é bloqueada.

---

## 8. Regras de Alocação

### Kit Padrão por Área

Cada área tem um kit mínimo:

| Área | Kit |
|------|-----|
| Qualquer área | notebook + headset + kit teclado e mouse |
| Desenvolvimento | kit padrão + monitor |
| Design | kit padrão + monitor |
| Demais áreas | kit padrão (sem monitor) |

### Resolução de Pessoa

O campo `com_quem` aceita:

- **ID**: `C-019` (exato)
- **E-mail**: `juliana.rocha@t4h.exemplo` (exato)
- **Nome**: `Juliana` (substring, sem acento)

Se o nome bater com mais de uma pessoa, retorna erro `422` com as opções.

### Alocação sem Dono

```python
if status in ["reservado", "alocado"] and not com_quem:
    return False, "com_quem é obrigatório"
```

Não é possível reservar/alocar sem informar para quem.

---

## 9. Regras de Devolução

### Devolução Física Comprovada

Há 3 formas de comprovar devolução:

#### 1. Evento do cenário com patrimônios específicos

```json
{
  "devolve": {
    "patrimonios": ["EQ-0002", "EQ-0051"]
  }
}
```

#### 2. Evento do cenário com cota por tipo

```json
{
  "devolve": {
    "colaborador": "C-026",
    "tipo": "headset",
    "quantidade": 2
  }
}
```

#### 3. Resposta automática a mensagem com "devol"

- Pessoa recebe mensagem com "devol" no assunto/corpo
- 70% de chance: responde confirmando devolução
- 30% de chance: promete devolver depois

### O que NÃO comprova devolução

- Evento criado no painel
- Mudar status do evento
- Criar observação
- Dizer que devolveu sem evento/resposta

---

## 10. Regras de Compra

### Prazo de Entrega

| Tipo | Prazo |
|------|-------|
| Notebook | 10 dias úteis |
| Monitor | 7 dias úteis |
| Headset | 3 dias úteis |
| Kit teclado e mouse | 3 dias úteis |
| Carregador | 5 dias úteis |

### Processo de Compra

1. Agente identifica necessidade (estoque baixo, alocação sem estoque)
2. Consulta catálogo de preços
3. Se valor ≤ R$ 500 → PROPÕE (pode ser aprovado)
4. Se valor > R$ 500 → ESCALA (requer alçada superior)
5. Compra é feita no portal do fornecedor
6. Fornecedor entrega na data prevista
7. Novo evento chega confirmando entrega
8. Itens viram `disponível`/`novo` no inventário

---

## 11. Regras de Observabilidade

### Rastreamento de Ações

Cada ação executada é registrada com:

- `ferramenta`: qual MCP tool foi usada
- `agente`: qual agente executou
- `agora`: timestamp da execução

### Tokens Rastreados

O sistema conta tokens usados em chamadas LLM para observabilidade:

- Classificação de evento
- Extração de entidades
- Redação de resposta

---

## 12. Resumo Visual das Regras

```
┌─────────────────────────────────────────────────────────────┐
│ REGRAS DE NEGÓCIO — GESTÃO DE EQUIPAMENTOS                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 💰 FINANCEIRO                                               │
│   • Limite de compra autônoma: R$ 500                       │
│   • Acima: ESCALA                                           │
│   • Abaixo: PROPÕE                                          │
│                                                             │
│ 📅 PRAZOS                                                   │
│   • Devolução após saída: 5 dias (não cobrar)              │
│   • Cobrança: 5–10 dias úteis                              │
│   • Escalação: > 10 dias úteis                             │
│   • Empréstimo máximo: 7 dias úteis                        │
│   • Kit pronto: 2 dias úteis antes da entrada              │
│                                                             │
│ 📦 ESTOQUE                                                  │
│   • Mínimo por tipo: 3 itens                               │
│   • Alerta se < 3                                          │
│                                                             │
│ 🔐 SEGURANÇA                                                │
│   • Bloquear e-mail externo                                │
│   • Validar pessoa (não saiu)                              │
│   • Validar item (novo/usado)                              │
│   • Detectar duplicidade                                   │
│                                                             │
│ 🎯 AUTONOMIA                                                │
│   • FAZ_SOZINHO: dúvida, consulta, devolução              │
│   • PROPÕE: empréstimo, compra ≤ R$ 500                   │
│   • ESCALA: baixa, compra > R$ 500, exceções              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Referências

- [Documentação Técnica](DOCUMENTACAO_TECNICA.md) — Contrato MCP, bases de dados, eventos
- [Estrutura do Projeto](../ESTRUTURA.txt) — Layout e componentes
- [Código de Regras](../src/rules.py) — Implementação em Python
