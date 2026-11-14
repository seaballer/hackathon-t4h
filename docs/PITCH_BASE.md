# Base para pitch — Colaborador Digital

**Formato:** roteiro de 8 slides para apresentação de 5–7 minutos  
**Público:** banca de hackathon, gestão de TI e potenciais usuários  
**Nota:** métricas de impacto ainda não foram medidas. Os slides evitam prometer ganhos quantitativos sem evidência.

---

## Slide 1 — Colaborador Digital: gestão de equipamentos com agentes

**Na tela**
- Automatizar o atendimento e as rotinas de inventário de TI.
- Do evento recebido à ação registrada, com regras de negócio no fluxo.
- Protótipo para o Hackathon UNIFEI 2026.

**Fala sugerida**  
“A proposta é transformar solicitações dispersas sobre equipamentos em um fluxo rastreável: entender o pedido, consultar o inventário, aplicar políticas e executar ou encaminhar a ação.”

**Visual**  
Uma solicitação entrando, passando por decisão e resultando em inventário atualizado e resposta.

---

## Slide 2 — O problema operacional

**Na tela**
- Pedidos chegam em formatos variados e exigem interpretação.
- Disponibilidade, responsável e situação do equipamento precisam ser conferidos.
- Ações incorretas geram duplicidade, conflito de inventário e atendimento incompleto.
- Exceções e aprovações precisam ficar visíveis para a equipe.

**Fala sugerida**  
“Uma solicitação simples pode exigir várias consultas e atualizações. O desafio é reduzir o trabalho repetitivo sem perder controle sobre decisões que precisam de uma pessoa.”

**Visual**  
Inbox fragmentada → conferências manuais → risco de erro/atraso.

---

## Slide 3 — A solução proposta

**Na tela**
- Um cliente Python consome eventos de um mundo simulado via MCP Streamable HTTP.
- Um grafo LangGraph coordena nove etapas: receber, classificar, resolver dados, planejar, validar, aprovar, executar, registrar e responder.
- Regras determinísticas complementam a classificação por LLM.
- Ações suportadas atualizam as bases e o evento recebe uma resposta.

**Fala sugerida**  
“O LLM ajuda a interpretar a linguagem do pedido; as regras locais decidem limites e condições. O grafo conecta essas etapas e o MCP funciona como interface com eventos e inventário.”

**Visual**

```text
Evento → Classificar → Consultar → Planejar → Validar → Aprovar
                                                     ↓
                                      Executar → Registrar → Responder
```

---

## Slide 4 — Como funciona na prática

**Na tela**
1. Recebe um evento da fila MCP.
2. Classifica intenção e extrai entidades com LLM; há fallback por palavras-chave.
3. Consulta inventário/colaboradores quando a ação depende do estado atual.
4. Monta plano por tipo de evento e valida campos/regras.
5. Executa ações permitidas, registra resultados e responde.

**Exemplo: reserva de kit**
- Identifica colaborador e itens necessários.
- Consulta regras de kit e encontra equipamentos disponíveis.
- Reserva itens atualizando status e responsável.
- Se uma atualização falha no meio, tenta reverter as reservas já feitas.

**Fala sugerida**  
“O sistema não deve confiar apenas no texto recebido: ele consulta o estado do equipamento antes de agir. No caso de um kit, escolhe itens elegíveis, reserva e tenta rollback se uma etapa falhar.”

---

## Slide 5 — Controles e arquitetura

**Na tela**
- Regras locais: autonomia por tipo, empréstimo de até 7 dias úteis, estoque mínimo e limites definidos no código.
- Validação de campos e estado antes de algumas atualizações.
- Cliente MCP com sessão, suporte a JSON/SSE, timeout, retry de 503 e circuit breaker.
- Cache de idempotência em memória para algumas operações.
- Logs e relatório final de eventos, tokens e erros.

**Fala sugerida**  
“A arquitetura separa interpretação de política: regras são código testável. Há mecanismos de resiliência no transporte e registro para facilitar demonstrações e depuração.”

**Visual**  
Cliente (LangGraph + LLM + regras) ↔ MCP (eventos e bases) → painel do cenário.

---

## Slide 6 — Escopo demonstrável hoje

**Na tela**
- Fluxo principal implementado como nós LangGraph.
- Classificação via LiteLLM e modo offline/fallback.
- Playbooks para dúvidas, consultas, devoluções, alocação/reserva, entrada/saída, baixa, empréstimo e entrega.
- Testes unitários existentes para regras, relógio, cliente MCP, nós e grafo.
- Integração esperada com servidor MCP real do hackathon; existe também um mock legado no repositório.

**Fala sugerida**  
“O repositório já materializa o fluxo de processamento e possui testes focados nos módulos. O próximo passo é demonstrar os playbooks ponta a ponta no servidor oficial e medir resultados.”

**Visual**  
Marcar como “implementado”, “integração a demonstrar” e “próximo passo”; não apresentar metas como resultados medidos.

---

## Slide 7 — Lacunas para fechar o fluxo técnico

**Na tela**
- **Aprovação humana:** níveis `PROPOE` e `ESCALA` são bloqueados, mas não há fila, tela ou mecanismo para aprovar/rejeitar e retomar o evento.
- **Ações MCP:** alguns planos usam operações locais (`alocar_item`, `baixar_item`, etc.) que são traduzidas para `atualizar`; outras, como `registrar_entrada`/`registrar_saida` como registro de RH e compra no portal, não têm fluxo completo. O `registrar` no Tema 3 é descrito como indisponível.
- **Falhas ambíguas:** após timeout/504 em mutação, é preciso consultar o estado antes de repetir. O cliente atual não implementa essa reconciliação como política geral.
- **Idempotência e retomada:** cache é em memória; não sobrevive reinício. O grafo instancia checkpoint, mas execução compartilha `thread_id="main"`, não um identificador por evento.
- **Tratamento de erro/estado:** falha ao aguardar evento pode voltar ao loop; saída sem evento não limpa explicitamente campos antigos. Revisar política de retry para não perder ou reapresentar evento.
- **Documentação desatualizada:** README/índice/AGENTES descrevem pasta `src/agents` e papéis diferentes dos `src/nodes` reais. README promete CLI `--help` com opções que não estão implementadas (p.ex. `--max-eventos` está documentado, mas ausente do parser atual? confirmar no ponto de entrada antes da apresentação). `DOCUMENTACAO_TECNICA.md` é principalmente contrato do servidor, não especificação completa do cliente.

**Fala sugerida**  
“A principal lacuna não é classificar o pedido: é fechar o ciclo de exceções. Precisamos de aprovação retomável, reconciliação segura após falha ambígua, idempotência persistente e documentação alinhada ao código.”

**Visual**  
Três colunas: “Pronto”, “Precisa integração”, “Próxima entrega”.

---

## Slide 8 — Próximos passos e convite

**Na tela**
1. Definir alçadas e implementar aprovação humana com retorno ao evento.
2. Completar playbooks apenas para operações existentes no servidor; integrar portal de fornecedor onde exigido.
3. Tornar retry seguro: reconciliação de estado em 504/409 e ledger persistente por evento/ação.
4. Rodar cenários ponta a ponta no MCP oficial e medir tempo, taxa de sucesso, conflitos e intervenções humanas.
5. Atualizar README, fluxo, índice e critérios de aceite para refletir o produto real.

**Fala sugerida**  
“A próxima fase transforma o protótipo em uma demonstração confiável: aprovação com humano no ciclo, execução segura e métricas observadas. Buscamos validar esses fluxos com a banca e com a equipe de operações.”

**Fechamento**  
“Colaborador Digital: automação de rotina com decisão rastreável e supervisão humana onde ela importa.”

---

# Apêndice — explicação do repositório

## Componentes

- `main.py`: carrega `.env`, inicia MCP/LLM/regras/grafo, roda o laço e imprime resumo.
- `src/graph.py`: define o fluxo LangGraph e as transições condicionais.
- `src/nodes/`: nove nós funcionais; são funções sobre estado compartilhado, não agentes autônomos independentes.
- `src/state.py`: formato dos dados que percorrem o grafo.
- `src/rules.py`: políticas e validações em Python.
- `src/llm.py`: classificação, extração e redação com LiteLLM; fallback de classificação por palavras-chave.
- `src/mcp_client.py`: sessão JSON-RPC MCP, decodificação JSON/SSE, ferramentas, retry limitado para 503 e cache de idempotência em memória.
- `src/clock.py`: relógio e cálculo de dias úteis.
- `src/mcp_server.py`: mock FastAPI antigo; não representa o servidor MCP Streamable HTTP documentado.
- `tests/`: testes unitários dos componentes; não substituem validação ponta a ponta contra o servidor do hackathon.

## Fluxo implementado

`aguardar_evento → classificar → resolver_dados → montar_plano → validar → aprovar → executar → registrar → responder → aguardar_evento`

Se `aprovar` encontra bloqueios ou ação não autônoma, o fluxo volta a aguardar eventos sem executar nem abrir uma aprovação humana. Ao encerrar, o grafo termina. Há tratamento de exceções em nós individuais, mas não existe um estado de falha operacional uniforme nem recuperação guiada para todos os casos.

## O que a documentação técnica do servidor não fecha para este cliente

`docs/DOCUMENTACAO_TECNICA.md` explica muito bem o contrato MCP e o mundo simulado (ferramentas, bases, estados, eventos, portal e falhas). Ela não substitui a documentação de implementação do cliente. Para completar o fluxo de engenharia e operação, falta registrar:

1. **Mapeamento playbook → API MCP:** ferramenta real chamada, base/campos alterados, precondições e efeito esperado por tipo.
2. **Matriz de cobertura:** eventos suportados, parcialmente suportados e não suportados, incluindo o portal legado.
3. **Máquina de estados do cliente:** estados do evento, transições, saída de aprovação, rejeição, falha e retomada.
4. **Contrato de autonomia:** quem pode aprovar, como a aprovação chega, expira, é auditada e retoma o mesmo evento.
5. **Semântica de falha por operação:** retry, reconciliação após 504, conflitos 409, rollback e limites do rollback parcial.
6. **Persistência:** escopo do checkpoint, `thread_id`, sobrevivência a reinício e armazenamento do ledger idempotente.
7. **Observabilidade e aceite:** logs/campos, métricas definidas, cenários ponta a ponta e critérios verificáveis de sucesso.
8. **Execução real:** instalação, configuração de MCP/LLM, comportamento offline, limites CLI e encerramento operacional.
9. **Alinhamento documental:** corrigir árvore de arquivos, papéis, opções de execução e fluxos divergentes em README, índice, AGENTES e FLUXO.

## Alertas de precisão para a apresentação

- Dizer “grafo de nove nós”, não “quatro agentes autônomos”: a implementação presente tem nove nós procedurais; a pasta `src/agents` citada em documentos não existe.
- O fluxo de aprovação não está completo: `PROPOE`/`ESCALA` são recusados pelo nó de aprovação por falta da fila humana.
- O cache idempotente é local e volátil; não alegar garantia de exatamente uma execução.
- O servidor mock incluído é legado e usa rotas REST diferentes do contrato MCP real.
- As regras de autonomia no código precisam de alinhamento com a documentação do servidor antes de serem apresentadas como política final.
- Não afirmar economia, velocidade, acurácia ou cobertura sem execução controlada e métricas coletadas.
