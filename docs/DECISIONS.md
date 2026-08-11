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

Nenhuma decisão aprovada deve ser silenciosamente substituída. Alterações exigem nova entrada neste arquivo explicando decisão anterior, nova decisão, motivo e impactos.

---

## D-015 — Um chat dedicado por fase
**Status:** aprovado

Cada fase do roadmap deve ser trabalhada preferencialmente em um chat/sessão dedicado. O chat da FASE 0 permanece como espaço de Foundation e governança transversal, sem implementar funcionalidades das fases posteriores.

**Motivo:** reduzir mistura de contexto, facilitar retomada, diminuir interpretações cruzadas entre fases e tornar o handoff explícito.

---

## D-016 — Lifecycle de fase padronizado por skills
**Status:** aprovado

O repositório mantém duas skills instruction-only:

- `chartvision-phase-start` para reconstruir contexto, validar autorização e produzir Phase Brief;
- `chartvision-phase-close` para verificar Definition of Done, persistir memória e somente então permitir PASS.

**Motivo:** transformar início e fechamento de fase em procedimentos repetíveis, auditáveis e resistentes à perda de contexto.

---

## D-017 — Instrução do Projeto ChatGPT versionada no repositório
**Status:** aprovado

A instrução usada no Projeto do ChatGPT deve possuir cópia canônica em `docs/CHATGPT_PROJECT_INSTRUCTIONS.md`.

**Motivo:** impedir deriva entre configuração externa do ChatGPT e memória operacional do GitHub.

---

## D-018 — Outcome Evaluation usa Ground Truth pós-análise com Outcome imutável 1:1
**Status:** aprovado

A FASE 7 deve preservar a separação temporal entre análise e avaliação:

- `Analysis(T)` usa somente informação conhecida até `T` e permanece imutável;
- Ground Truth posterior entra somente por um contrato dedicado de avaliação (`GroundTruthProvider` ou equivalente), nunca por `AnalysisEngine` ou `AnalysisLabService`;
- a avaliação usa o último candle Ground Truth fechado em ou antes de `T` como referência e exige um horizonte explícito de candles futuros fechados integralmente disponível;
- o resultado realizado possui somente `UP`, `DOWN` ou `SIDEWAYS`; `UNCERTAIN` permanece abstention da Analysis;
- no MVP existe no máximo um Outcome imutável por Analysis e sua identidade é `analysis_id`;
- métricas agregadas são derivadas de `Analysis + Outcome` e não exigem tabela persistida própria no MVP.

**Motivo:** resolver a fronteira de Ground Truth sem future leakage, manter auditoria simples, impedir reescrita histórica e evitar complexidade prematura de múltiplos horizontes/configurações ou persistência de agregados.

**Contrato detalhado:** `docs/outcome_evaluation.md`.
