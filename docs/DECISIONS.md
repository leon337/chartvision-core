# ChartVision Core — Registro de Decisões

Este arquivo registra decisões já aprovadas para evitar reinterpretação futura.

## D-001 — Núcleo universal, fontes desacopladas
**Status:** aprovado

O núcleo não conhece plataformas específicas. Toda fonte deve entrar por contratos como `ChartSource` e produzir dados canônicos.

**Motivo:** permitir reutilização futura do motor sem reescrever análise, memória ou avaliação.

---

## D-002 — Replay controlado antes de integrações externas
**Status:** aprovado

O v1 começa com `ReplaySource` e gráfico controlado.

**Motivo:** validar arquitetura, leitura visual e avaliação com Ground Truth conhecido antes de qualquer adapter externo.

---

## D-003 — Visão computacional não acessa Ground Truth
**Status:** aprovado

O leitor visual recebe somente a imagem renderizada. OHLC verdadeiros ficam isolados para avaliação.

**Motivo:** impedir falsa validação e medir a capacidade real do pipeline visual.

---

## D-004 — Captura periódica não equivale a nova análise
**Status:** aprovado

Intervalo inicial de captura: 5 segundos. Várias capturas podem representar o mesmo candle.

**Motivo:** separar observação, consolidação temporal e análise.

---

## D-005 — OpenCV é parte do leitor, não o motor completo
**Status:** aprovado

OpenCV trata localização, formas, corpos, pavios, cores e geometria. OCR fica atrás de contrato próprio quando necessário. Tracking e normalização são componentes separados.

**Motivo:** evitar componente monolítico e melhorar testabilidade.

---

## D-006 — Banco temporal estruturado
**Status:** aprovado

Persistir sessões, frames, observações, candles, features, análises e outcomes com timestamps e rastreabilidade.

**Motivo:** permitir memória histórica e auditoria.

---

## D-007 — PostgreSQL no v1
**Status:** aprovado

Não adicionar Redis, banco vetorial ou TimescaleDB no v1.

**Motivo:** reduzir complexidade até existir necessidade comprovada.

---

## D-008 — Análise deve poder recusar resposta
**Status:** aprovado

`UNCERTAIN` e estados de falha são resultados válidos.

**Motivo:** impedir que baixa qualidade visual produza conclusões aparentemente confiáveis.

---

## D-009 — Sem future leakage
**Status:** aprovado

O AnalysisEngine só pode consumir informação existente até o instante da análise.

**Motivo:** preservar validade do laboratório e das métricas.

---

## D-010 — Previsões são imutáveis após registro
**Status:** aprovado

OutcomeEvaluator adiciona resultado posterior, mas não altera retrospectivamente a análise original.

**Motivo:** garantir avaliação honesta e auditável.

---

## D-011 — Fases pequenas e gates obrigatórios
**Status:** aprovado

O desenvolvimento segue FASE 0 → FASE 8. Uma fase só avança com critérios verificáveis.

**Motivo:** reduzir scope creep, economizar execução e facilitar diagnóstico.

---

## D-012 — Codex recebe missões estreitas
**Status:** aprovado

Codex não recebe o produto inteiro como tarefa aberta. Recebe somente a fase autorizada, com critérios de aceite e proibições explícitas.

**Motivo:** reduzir consumo de cota e evitar decisões arquiteturais divergentes.

---

## D-013 — GitHub é a memória oficial
**Status:** aprovado

Roadmap, escopo, decisões e estado atual devem ser persistidos neste repositório. Chats são contexto auxiliar, não fonte final de verdade.

**Motivo:** permitir retomada consistente em novos chats, agentes e sessões.

---

## D-014 — Mudança de decisão exige registro
**Status:** aprovado

Nenhuma decisão acima deve ser silenciosamente substituída. Alterações exigem nova entrada neste arquivo explicando:
- decisão anterior;
- nova decisão;
- motivo;
- impacto no roadmap;
- impacto no escopo;
- data/commit de adoção.