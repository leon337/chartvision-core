# ChartVision Core — Roadmap Oficial

> Status: **FROZEN v1**
>
> Este documento é a fonte de verdade para a sequência de desenvolvimento. Nenhuma fase pode ser pulada, ampliada ou reordenada sem decisão explícita registrada em `docs/DECISIONS.md` e atualização de `docs/SCOPE.md`.

## Estado global

| Fase | Nome | Estado |
|---|---|---|
| 0 | Foundation | ✅ PASS |
| 1 | Replay MVP | ✅ PASS |
| 2 | Visual Observer MVP | ✅ PASS |
| 3 | Candle Reconstruction MVP | ✅ PASS |
| 4 | Temporal Memory MVP | ✅ PASS |
| 5 | Market Features MVP | ✅ PASS |
| 6 | Analysis Lab MVP | ✅ PASS |
| 7 | Outcome Evaluation MVP | ⬜ PENDING |
| 8 | Dashboard MVP | 🔒 BLOCKED |

A FASE 7 é a única próxima fase autorizável. `PENDING` não significa iniciada: sua abertura exige novo chat dedicado e novo `chartvision-phase-start = READY`. A FASE 8 continua bloqueada e dependente do PASS sequencial da FASE 7.

## Regra de progressão

Uma fase somente muda para `PASS` quando:
1. a implementação do escopo da fase está completa;
2. testes definidos para a fase passam;
3. CI passa;
4. critérios de aceite foram verificados com evidência;
5. ausência de regressão/scope creep relevante foi verificada;
6. `docs/PROJECT_STATE.md` foi atualizado;
7. este roadmap e a Issue Mestra #1 foram atualizados;
8. o procedimento `chartvision-phase-close` resultou em PASS ou foi reproduzido integralmente.

Executar código não significa concluir uma fase.

## Lifecycle de cada fase

Antes de implementar:

```text
chartvision-phase-start
→ recuperar estado real
→ confirmar fase autorizada
→ produzir Phase Brief
```

Depois da implementação e testes:

```text
chartvision-phase-close
→ validar Definition of Done
→ persistir memória
→ PASS / FAIL / BLOCKED
```

O PASS de uma fase apenas autoriza abrir o chat da próxima fase. Não inicia automaticamente sua implementação.

---

## FASE 0 — FOUNDATION — ✅ PASS

### Objetivo
Estabelecer a base executável, testável e governável do projeto.

### Evidência
Foundation validada com FastAPI, React + TypeScript + Vite, PostgreSQL, Docker Compose, health check, testes, lint, build frontend, CI e governança persistente.

---

## FASE 1 — REPLAY MVP — ✅ PASS

### Objetivo
Reproduzir um dataset OHLC de forma determinística em um gráfico controlado.

### Entregas concluídas
- `ReplaySource`;
- dataset de referência;
- `ChartRenderer`;
- Start/Pause/Resume/Reset;
- relógio virtual determinístico;
- gate temporal contra exposição antecipada de candles.

### Evidência de fechamento
- PR `#2` — merged;
- HEAD técnico `f335a35bbd028e4e8050d995fea8b4c5a907a0a5`;
- merge `821bce313295701fd69cd1925fa9f4a3726cb731`;
- CI final run `#32` / `31374719545` — SUCCESS.

---

## FASE 2 — VISUAL OBSERVER MVP — ✅ PASS

### Objetivo
Observar o gráfico renderizado estritamente como imagem.

### Entregas concluídas
- `CaptureService`;
- `ChartDetector`;
- `CandleDetector`;
- contratos de geometria/confiança/qualidade/falhas;
- `OpenCVVisionProvider.observe(image: bytes)`;
- cenário visual controlado.

### Evidência de fechamento
- branch `phase-2-visual-observer-mvp`;
- PR `#3` — merged;
- HEAD técnico `83d5b8dc7c94fdc472a3049bb30f835454e45d1a`;
- merge `afc028a6c966ec8be628dee59b9aa432ebd8921c`;
- HEAD documental anterior `d0f28b87d4d8d9bfb8e2e706b7711d842ecad060`;
- CI final run `#37` / `31408563320` — SUCCESS.

### Critérios de aceite verificados
- visão recebe somente imagem/pixels e não acessa OHLC/Ground Truth;
- candles visíveis são identificados com geometria, direção e confiança;
- falhas retornam estados explícitos;
- `Frame` permanece separado de candle;
- pixel→preço, tracking e normalização não foram antecipados.

---

## FASE 3 — CANDLE RECONSTRUCTION MVP — ✅ PASS

### Objetivo
Converter elementos visuais em candles normalizados e compará-los ao Ground Truth somente após a reconstrução.

### Entregas concluídas
- `OpenCVPriceScaleReader` controlado para anchors derivados dos pixels da escala;
- `PriceMapper`;
- `ChartTracker`;
- `Normalizer`;
- reconstrução OHLC;
- identificação de candle aberto/fechado;
- reconhecimento de novo candle e deslocamento horizontal;
- deduplicação temporal limitada à reconstrução;
- `TRACKING_LOST` como falha explícita;
- `CandleReconstructionPipeline` sem Ground Truth;
- `ReconstructionEvaluator` pós-reconstrução.

### Métricas implementadas
- Open error;
- High error;
- Low error;
- Close error;
- candle detection rate;
- direction accuracy;
- duplicate rate;
- missing candle rate.

### Evidência de fechamento
- branch `phase-3-candle-reconstruction-mvp`;
- HEAD técnico `b5dd7abecc8402ff825204b2bfe32cd158d2e483`;
- PR `#6 — feat: complete Phase 3 Candle Reconstruction MVP` — merged;
- merge em `main` `58f202e6ca1bfea3bf6f1f08a737a78bd3e3b71c`;
- CI técnico run `#42` / `31419351907` — SUCCESS;
- CI do PR run `#43` / `31419606685` — SUCCESS;
- CI pós-merge run `#44` / `31419758543` — SUCCESS;
- suíte específica da FASE 3 — `27 passed`;
- lint, backend, frontend e stack Docker — SUCCESS.

---

## FASE 4 — TEMPORAL MEMORY MVP — ✅ PASS

### Objetivo
Persistir a evolução temporal do gráfico com integridade e rastreabilidade.

### Entregas concluídas
- `sessions`;
- `frames`;
- `observations`;
- `candles`;
- timestamps timezone-aware normalizados para UTC;
- deduplicação persistente;
- fechamento de candle persistido;
- snapshots imutáveis de candle por observação;
- rastreabilidade `Frame → Observation → dado reconstruído`.

### Contrato temporal validado
- `Session` usa `session_id` como identidade persistente;
- `Frame` usa `frame_id`, sem tratar `image_hash` como identidade temporal;
- `Observation` referencia o `Frame` da mesma sessão;
- candle canônico usa `(session_id, open_time)` como identidade no v1;
- candle aberto pode evoluir sem duplicação;
- candle fechado é imutável;
- snapshots históricos são preservados e auditáveis;
- divergências/regravações incompatíveis produzem erro explícito.

### Evidência de fechamento
- branch `phase-4-temporal-memory-mvp`;
- HEAD técnico `4e87314e7711464d3f08841c594330ecd235bd46`;
- PR `#7 — feat: complete Phase 4 Temporal Memory MVP` — merged;
- merge funcional em `main` `f0fac60c1ba0f24ddee7ed76f512600070acdf60`;
- CI técnico da branch: run `#69` / `31438663542` — SUCCESS;
- CI do PR: run `#70` / `31438809722` — SUCCESS;
- CI pós-merge: run `#71` / `31438952349` — SUCCESS;
- HEAD documental final `9d1cdd7b44c6c1f1c8f526b8c195cf36bd3e29c9`;
- CI final documental run `#74` / `31439159599` — SUCCESS.

---

## FASE 5 — MARKET FEATURES MVP — ✅ PASS

### Objetivo
Gerar características estruturadas a partir dos candles normalizados.

### Escopo congelado concluído
- direção;
- amplitude;
- retorno;
- volatilidade simples;
- HH, HL, LH, LL;
- tendência básica;
- lateralização básica.

Além das dez features, a fase estabeleceu e validou a primitive point-in-time `get_candles_as_of(session_id, as_of)` necessária para que os cálculos operem somente sobre informação conhecida no instante analisado, e formalizou o contrato em `docs/market_features.md`.

### Fronteira temporal validada

```text
Temporal Memory
→ get_candles_as_of(session_id, as_of)
→ candles conhecidos naquele instante
→ Market Features
```

O teste PostgreSQL point-in-time comprova que snapshots posteriores não alteram leituras históricas, o estado canônico futuro não é usado retroativamente, `as_of` é timezone-aware, sessões permanecem isoladas e observações futuras são excluídas. Lacunas não são preenchidas.

### Dez features validadas
1. direção: `close > open`, `<` ou `==`, com enum próprio da FASE 5;
2. amplitude: `high - low`;
3. retorno: `(close_t - close_prev) / close_prev`, predecessor fechado e zero → `None`;
4. volatilidade: últimos N fechados, N>=3, N-1 retornos, variância populacional e raiz Decimal;
5. HH: `current.high > previous.high`;
6. HL: `current.low > previous.low`;
7. LH: `current.high < previous.high`;
8. LL: `current.low < previous.low`;
9. tendência: unanimidade estrutural dos pares em `RISING_STRUCTURE`, `FALLING_STRUCTURE` ou `MIXED_STRUCTURE`;
10. lateralização: `MIXED_STRUCTURE` e `range_ratio <= T`, com janela N>=3 e referência `abs(close_1)`.

### Política numérica e candle aberto
- cálculos derivados usam `Decimal`;
- divisões/raiz que exigem controle usam precisão 28 e `ROUND_HALF_EVEN` em contexto local;
- não há `float` ou `quantize` nos cálculos de features;
- direção e amplitude permitem alvo aberto;
- retorno permite alvo aberto, mas exige predecessor fechado;
- volatilidade, HH/HL/LH/LL, tendência e lateralização usam somente candles fechados;
- lateralização possui regressão explícita contra influência do contexto Decimal global.

### Gate — PASS
Revisão completa do diff desde o HEAD formal da FASE 4 confirmou 45 commits e 19 arquivos da FASE 5, sem implementação de FASE 6.

Evidências:
- branch `phase-5-market-features-mvp`;
- HEAD final da branch: `c3d6991a78b92d114df9cafb14bf8586d9d41320`;
- CI final da branch: run `#120` / `31464324474` — SUCCESS;
- PR `#8 — feat: complete Phase 5 Market Features MVP` — merged;
- CI do PR: run `#121` / `31465714858` — SUCCESS;
- merge funcional em `main`: `c276b966738abd65ac6c0658e5a9771d558fdb29`;
- CI pós-merge: run `#122` / `31465857520` — SUCCESS;
- `ruff check app` — SUCCESS;
- `pytest -q` — `137 passed, 34 skipped`;
- PostgreSQL real Phase 4/5 — `34 passed`;
- migrations `upgrade head`, `downgrade base` e novo `upgrade head` — SUCCESS;
- frontend build — SUCCESS;
- Docker Compose, backend health e frontend — SUCCESS;
- governance-memory — SUCCESS.

O HEAD documental final e seu CI são registrados na Issue Mestra #1 depois que o CI do commit de fechamento termina, evitando referência recursiva em arquivo versionado.

### Revisão de escopo
Não foram implementados `AnalysisEngine`, `UP`, `DOWN`, `SIDEWAYS`, `UNCERTAIN`, previsão, sinais, Outcome Evaluation, Dashboard, execução financeira, integração com corretoras ou qualquer funcionalidade da FASE 6+. A lateralização booleana não é o estado `SIDEWAYS`.

### Arquitetura
`FeatureEngine` permanece domínio puro, sem SQLAlchemy, psycopg, `app.infrastructure`, PostgreSQL, ReplaySource ou Ground Truth. A primitive point-in-time permanece anterior ao cálculo, no contrato/storage.

### Decisões
Nenhuma nova decisão arquitetural material foi necessária. `docs/DECISIONS.md` permaneceu inalterado.

### Limitações conhecidas
- v1 restrito a replay/ambiente controlado;
- métodos de feature não sintetizam gaps e pressupõem a ordem temporal dos candles fornecidos pela fronteira point-in-time;
- janelas contam candles elegíveis;
- lateralização permanece booleana e não executa classificação de análise;
- warning deprecado do Alembic sobre `path_separator` permanece não bloqueante.

---

## FASE 6 — ANALYSIS LAB MVP — ✅ PASS

### Objetivo
Classificar deterministicamente o estado conhecido do gráfico usando somente informação disponível até `as_of`, com persistência imutável e auditável da decisão.

### Entregas concluídas
- `AnalysisConfig` e `AnalysisDecision` imutáveis;
- `MarketState.UP`, `DOWN`, `SIDEWAYS` e `UNCERTAIN`;
- `AnalysisEngine` puro, determinístico e sem storage/Ground Truth/Replay/OutcomeEvaluator;
- `AnalysisLabService` com fronteira `get_candles_as_of(session_id, as_of)`;
- política estrutural de candles fechados;
- `required_closed_candles = max(trend_pairs + 1, lateralization_window_candles)`;
- `data_quality` pela menor `vision_confidence` da janela fechada requerida;
- gate de qualidade e precedência HISTÓRICO → QUALIDADE → SIDEWAYS → UP/DOWN → UNCERTAIN;
- `Analysis.timestamp == as_of`;
- `StorageProvider.save_analysis` / `get_analysis`;
- `AnalysisConflictError`;
- `AnalysisRecord`;
- migration `0005_create_analyses`;
- `analyze_and_record`;
- idempotência por `analysis_id`, conflito explícito e imutabilidade;
- evidence determinística, ordenada e auditável.

### Anti-future-leakage
Foram comprovados no fluxo completo `AnalysisLabService.analyze(as_of=T)`:
- candle futuro não altera `AnalysisDecision` histórico;
- snapshot futuro não altera `AnalysisDecision` histórico;
- evolução futura do mesmo candle canônico não altera `AnalysisDecision` histórico.

Também foi validado o cenário persistente `analyze_and_record(T)` antes/depois de adicionar futuro, preservando a mesma `Analysis` e uma única linha persistida.

### Gate — PASS
Todos os 15 critérios de aceite canônicos foram verificados individualmente e passaram.

Evidências:
- branch `phase-6-analysis-lab-mvp`;
- HEAD técnico `dcf63c4670cdf316eaff3dbeab2141167ad836fd`;
- branch CI run `#134` / `31479821467`, attempt 4 — SUCCESS;
- PR `#9 — feat: complete Phase 6 Analysis Lab MVP` — merged;
- PR CI run `#135` / `31481693819` — SUCCESS;
- merge funcional em `main` `4a9b2035f098178f4bffd98a66603711f3397938`;
- CI pós-merge run `#136` / `31483381451` — SUCCESS;
- `ruff check app` — SUCCESS;
- `pytest -q` — `190 passed, 64 skipped`;
- PostgreSQL real FASES 4/5/6 — `64 passed, 6 warnings`;
- migrations `upgrade head`, `downgrade base` e novo `upgrade head` — SUCCESS;
- frontend build, Docker Compose, backend/frontend health e governance-memory — SUCCESS.

O HEAD documental final e seu CI são registrados na Issue Mestra #1 depois que o CI do commit de fechamento termina, evitando referência recursiva em arquivo versionado.

### Revisão de escopo
Não foram implementados OutcomeEvaluator funcional, Outcome model/persistence, OutcomeRecord, tabela `outcomes`, accuracy, precision, recall, confusion matrix, coverage, calibração por futuro, Dashboard, API/UI funcional de Analysis, novos indicadores, ML/RL, previsão/recomendação financeira, execução, corretoras ou dinheiro real. Nenhuma funcionalidade da FASE 7/8 foi iniciada.

### Decisões
Nenhuma nova decisão arquitetural material foi necessária. D-008, D-009 e D-010 já cobrem `UNCERTAIN`, anti-future-leakage e imutabilidade temporal da análise; `docs/DECISIONS.md` permanece inalterado.

### Limitações conhecidas
- v1 restrito a replay/ambiente controlado;
- classificação rule-based, sem inferência probabilística;
- `confidence` não é probabilidade estatística;
- `source_confidence` não participa de `data_quality`;
- avaliação de outcome e métricas de desempenho permanecem fora da FASE 6;
- API/UI funcional de Analysis permanece fora da FASE 6;
- warning deprectado do Alembic sobre `path_separator` permanece não bloqueante.

---

## FASE 7 — OUTCOME EVALUATION MVP — ⬜ PENDING

### Objetivo
Comparar análises registradas com o que ocorreu posteriormente no replay.

### Métricas
- accuracy;
- precision por classe;
- recall por classe;
- matriz de confusão;
- cobertura;
- quantidade de `UNCERTAIN`;
- calibração de confiança.

### Regra
A previsão original nunca pode ser alterada retrospectivamente.

### Autorização
É a próxima fase autorizável após o PASS formal da FASE 6. Deve iniciar somente em **novo chat dedicado** e depois de novo `chartvision-phase-start = READY`. Nenhuma implementação da FASE 7 ocorreu durante o fechamento da FASE 6.

---

## FASE 8 — DASHBOARD MVP — 🔒 BLOCKED

### Objetivo
Disponibilizar uma interface única para observação e auditoria do laboratório.

### Tela única
Deve apresentar gráfico, estado do replay, qualidade visual, estado estrutural, confiança, observações e métricas.

### Fora desta fase
Não criar páginas extras, multiusuário, notificações ou integrações externas.

### Bloqueio sequencial
Aguarda `PHASE_CLOSE = PASS` da FASE 7.

---

# Definition of Done do v1

O v1 somente estará concluído quando for possível executar e auditar de ponta a ponta:

```text
DATASET
  ↓
REPLAY
  ↓
GRÁFICO VISUAL
  ↓
CAPTURA
  ↓
VISÃO COMPUTACIONAL
  ↓
CANDLES RECONSTRUÍDOS
  ↓
MEMÓRIA TEMPORAL
  ↓
FEATURES
  ↓
ANÁLISE EXPERIMENTAL
  ↓
RESULTADO FUTURO
  ↓
AVALIAÇÃO
  ↓
DASHBOARD
```

O sucesso do v1 não é definido por rentabilidade financeira.

# Pós-v1

A arquitetura deve permitir futuros `ChartSource`/adapters, mas nenhuma integração externa faz parte do v1. Qualquer evolução pós-v1 exige novo escopo e decisão registrada.
