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

---

## D-019 — Target de Outcome é pré-comprometido por sessão e métricas usam cohort homogêneo
**Status:** aprovado

Esta decisão **estende D-018** sem alterar sua regra de imutabilidade `Analysis → Outcome`.

A FASE 7 deve impedir hindsight bias também na definição do target experimental:

- horizonte e threshold pertencem a uma `OutcomeEvaluationPolicy` identificada e imutável;
- no MVP existe no máximo uma policy por sessão/experimento;
- a policy registra `bound_at` a partir do relógio lógico autoritativo da sessão no instante do compromisso; o chamador não pode backdate esse valor;
- uma Analysis somente é elegível quando `policy.session_id == Analysis.session_id` e `policy.bound_at <= Analysis.timestamp`;
- uma policy criada depois dessa fronteira não torna Analysis histórica retroativamente elegível;
- `OutcomeEvaluationService` não aceita `OutcomeConfig` arbitrário no instante de avaliação; carrega a policy da sessão;
- cada Outcome registra `policy_id` e deve reproduzir exatamente horizonte e threshold da policy;
- no MVP, mudança de target exige nova sessão/experimento; múltiplas policies dentro da mesma sessão são `FUTURE`;
- todo relatório métrico corresponde a exatamente um `policy_id`;
- confusion matrix, accuracy, precision, recall, coverage, uncertain frequency e confidence calibration não podem agregar silenciosamente Outcomes de policies diferentes.

**Motivo:** impedir escolha retrospectiva de target depois de observar o futuro e evitar métricas que misturem definições incompatíveis de resultado realizado.

**Impactos:** futura persistência da FASE 7 precisa representar `outcome_evaluation_policies`; `Outcome` referencia policy; consultas de Outcomes para métricas devem preservar/validar cohort por `policy_id`. Nenhum código ou migration é criado por esta decisão documental.

**Contrato detalhado:** `docs/outcome_evaluation.md`.

---

## D-020 — Precommit usa exposure watermark não rebobinável
**Status:** aprovado

Esta decisão **estende e refina D-019** exclusivamente na prova temporal do precommit. As regras de policy imutável, uma policy por sessão, Outcome→Policy e cohort homogêneo de D-019 permanecem válidas.

O cursor operacional do replay e a memória experimental de exposição são conceitos distintos:

- `replay_cursor_time` representa a posição corrente da reprodução e pode ser rebobinado por `reset`;
- `session_exposure_watermark` representa a maior fronteira lógica de mercado já exposta na sessão/experimento;
- antes da primeira exposição, o watermark utiliza a origem lógica determinística e timezone-aware da sessão como baseline;
- o watermark é monotonicamente não decrescente durante toda a vida da sessão;
- avanço além do máximo anterior eleva o watermark;
- reset, pause/resume, stop ou reexecução abaixo do máximo anterior nunca reduzem o watermark;
- reset não cria silenciosamente uma nova sessão/experimento;
- `OutcomeEvaluationPolicy.bound_at` captura o `session_exposure_watermark` autoritativo no instante do registro, e não o cursor rebobinado;
- a comparação de elegibilidade permanece inclusiva: `policy.bound_at <= Analysis.timestamp`; igualdade pode ser elegível, enquanto `Analysis.timestamp < policy.bound_at` é rejeitado;
- uma Analysis anterior ao maior instante já exposto não se torna elegível por `reset`;
- mudar horizonte/threshold continua exigindo nova sessão/experimento no MVP;
- a futura persistência deve preservar/auditar o watermark através de múltiplos ciclos, reinvocação de serviço e restart, sem permitir regressão temporal;
- o watermark contém somente metadado temporal e não fornece OHLC, features ou Ground Truth ao `AnalysisEngine`, `AnalysisLabService`, FeatureEngine ou pipeline visual.

**Motivo:** o `ReplaySource.reset()` aprovado na FASE 1 rebobina o cursor/relógio corrente da reprodução. Se D-019 fosse interpretada como dependência desse cursor, seria possível observar futuro, resetar e registrar uma policy com falsa aparência de precommit. A fronteira monotônica elimina esse loophole sem alterar retroativamente a semântica funcional de reset da FASE 1.

**Impactos:** a implementação futura da FASE 7 deve manter estado auditável de exposição por sessão, capturar `bound_at` dessa fronteira e testar explicitamente reset/replay repetido. Não é criada migration, coluna, tabela ou alteração em `ReplaySource` por esta decisão documental.

**Contrato detalhado:** `docs/outcome_evaluation.md` e `docs/replay_system.md`.
