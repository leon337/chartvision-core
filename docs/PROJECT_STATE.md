# ChartVision Core — Estado Atual

> Este é o ponto de retomada operacional do projeto.
>
> Sempre ler este arquivo antes de iniciar uma nova missão.

## Estado atual

- **Versão de planejamento:** v1 congelado
- **Fase atual concluída:** FASE 5 — MARKET FEATURES MVP
- **Status:** ✅ PASS
- **Últimos PASS sequenciais:** FASE 0 — FOUNDATION; FASE 1 — REPLAY MVP; FASE 2 — VISUAL OBSERVER MVP; FASE 3 — CANDLE RECONSTRUCTION MVP; FASE 4 — TEMPORAL MEMORY MVP; FASE 5 — MARKET FEATURES MVP
- **Merge funcional da FASE 5:** `c276b966738abd65ac6c0658e5a9771d558fdb29`
- **CI pós-merge da FASE 5:** run `#122` / `31465857520` — SUCCESS
- **Próxima fase autorizável:** FASE 6 — ANALYSIS LAB MVP
- **Fases posteriores:** bloqueadas até PASS sequencial
- **Issue mestra:** `#1 — MASTER — ChartVision Core v1 Roadmap`
- **Modelo de trabalho:** um chat dedicado por fase + GitHub como memória oficial

O PASS da FASE 5 autoriza somente abrir a FASE 6 em um novo chat dedicado e executar/reproduzir `.agents/skills/chartvision-phase-start/SKILL.md`. A FASE 6 não foi iniciada neste fechamento.

## Evidência da FASE 1 — REPLAY MVP

A FASE 1 implementou replay determinístico, dataset de referência 1m, gate temporal, API Start/Pause/Resume/Reset/Advance, renderer controlado, controles no frontend e empacotamento Docker.

Referências:
- branch `phase-1-replay-mvp`;
- PR `#2` — merged;
- HEAD técnico `f335a35bbd028e4e8050d995fea8b4c5a907a0a5`;
- merge funcional `821bce313295701fd69cd1925fa9f4a3726cb731`;
- HEAD final de fechamento `b21ba9368a1dee5e1a067f1cb2b6ff1dd16f7ba6`;
- CI final run `#32` / `31374719545` — SUCCESS.

## Evidência da FASE 2 — VISUAL OBSERVER MVP

A FASE 2 implementou `CaptureService`, contratos visuais, `ChartDetector`, `CandleDetector`, `OpenCVVisionProvider`, confiança/qualidade e falhas explícitas, trabalhando estritamente com pixels.

Referências:
- branch `phase-2-visual-observer-mvp`;
- PR `#3` — merged;
- HEAD técnico `83d5b8dc7c94fdc472a3049bb30f835454e45d1a`;
- merge funcional `afc028a6c966ec8be628dee59b9aa432ebd8921c`;
- HEAD documental anterior `d0f28b87d4d8d9bfb8e2e706b7711d842ecad060`;
- CI final run `#37` / `31408563320` — SUCCESS.

## Evidência da FASE 3 — CANDLE RECONSTRUCTION MVP

### Escopo implementado
- `OpenCVPriceScaleReader` para extrair anchors de preço diretamente da escala visível do cenário controlado;
- `PriceMapper` com anchors visuais, orientação, validação, interpolação `Y → preço`, confiança e recusa de extrapolação;
- reconstrução de preços de corpo e pavios sem OHLC verdadeiro;
- `ChartTracker` para identidade entre frames, atualização de candle aberto, candle novo, fechamento, deslocamento horizontal e prevenção de duplicação;
- falha explícita `TRACKING_LOST`;
- `Normalizer` para `Candle` canônico, estado aberto/fechado, confiança e deduplicação limitada à reconstrução;
- `CandleReconstructionPipeline` sem Ground Truth como entrada;
- `ReconstructionEvaluator` separado para comparação posterior com Ground Truth;
- métricas Open/High/Low/Close error, candle detection rate, direction accuracy, duplicate rate e missing candle rate.

### Referências técnicas
- branch `phase-3-candle-reconstruction-mvp`;
- HEAD técnico `b5dd7abecc8402ff825204b2bfe32cd158d2e483`;
- PR `#6 — feat: complete Phase 3 Candle Reconstruction MVP` — merged;
- merge funcional em `main` `58f202e6ca1bfea3bf6f1f08a737a78bd3e3b71c`;
- CI técnico final da branch: run `#42` / `31419351907` — SUCCESS;
- CI do PR: run `#43` / `31419606685` — SUCCESS;
- CI pós-merge: run `#44` / `31419758543` — SUCCESS.

### Testes e critérios
- suíte específica da FASE 3: `27 passed`;
- `ruff check app` — SUCCESS;
- `pytest -q` — SUCCESS;
- `npm run build` — SUCCESS;
- stack Docker completa — SUCCESS;
- integração controlada comprovou atualização do mesmo candle sem duplicação, fechamento, deslocamento de `-70 px`, três candles fechados e métricas perfeitas no fixture controlado.

## Evidência da FASE 4 — TEMPORAL MEMORY MVP

### Escopo implementado
- persistência PostgreSQL de `Session`;
- persistência PostgreSQL de `Frame` com FK para `Session`;
- persistência PostgreSQL de `Observation` com vínculo consistente `Session` + `Frame`;
- persistência de `Candle` canônico por identidade `(session_id, open_time)`;
- timestamps timezone-aware normalizados para UTC;
- deduplicação persistente de sessões, frames, observações e candles;
- evolução persistida de candle aberto sem criar nova identidade;
- transição persistida de candle aberto para fechado;
- candle fechado imutável;
- snapshots imutáveis de candle por observação;
- rastreabilidade histórica `Frame → Observation → candle snapshot`;
- conflitos explícitos em vez de sobrescrita silenciosa;
- migrations Alembic `0001_create_sessions`, `0002_create_frames`, `0003_create_observations` e `0004_create_candles`.

### Integridade temporal comprovada
- o mesmo candle aberto pode evoluir mantendo uma única linha canônica;
- `high` não pode diminuir e `low` não pode aumentar em evolução temporal posterior;
- identidade/contexto/open/intervalo temporal do candle não podem ser alterados;
- candle fechado não pode ser reaberto ou reescrito;
- repetição do mesmo replay pode registrar novos frames/observações/snapshots sem regredir o estado canônico;
- resultados divergentes para o mesmo candle no mesmo timestamp lógico falham explicitamente;
- frames diferentes podem possuir o mesmo `image_hash`; hash visual não é usado como identidade temporal.

### Referências técnicas
- branch `phase-4-temporal-memory-mvp`;
- HEAD técnico final `4e87314e7711464d3f08841c594330ecd235bd46`;
- PR `#7 — feat: complete Phase 4 Temporal Memory MVP` — merged;
- merge em `main` `f0fac60c1ba0f24ddee7ed76f512600070acdf60`;
- CI técnico da branch: run `#69` / `31438663542` — SUCCESS;
- CI do PR: run `#70` / `31438809722` — SUCCESS;
- CI pós-merge: run `#71` / `31438952349` — SUCCESS;
- HEAD final documental/de fechamento em `main`: `9d1cdd7b44c6c1f1c8f526b8c195cf36bd3e29c9`;
- CI final do HEAD documental: run `#74` / `31439159599` — SUCCESS.

### Testes e critérios de aceite
No CI técnico/PR/pós-merge:
- `ruff check app` — SUCCESS;
- suíte backend sem variável de PostgreSQL: `47 passed, 31 skipped`; os 31 skips são os testes PostgreSQL executados separadamente;
- testes reais contra PostgreSQL: `31 passed`;
- migrations Alembic `upgrade head` até `0004` — SUCCESS;
- `downgrade base` seguido de novo `upgrade head` — SUCCESS;
- `npm run build` — SUCCESS;
- stack Docker completa e health checks — SUCCESS.

### Decisões
Nenhuma nova decisão arquitetural foi necessária para o fechamento. `docs/DECISIONS.md` permaneceu inalterado.

## Evidência da FASE 5 — MARKET FEATURES MVP

A FASE 5 foi encerrada formalmente após revisão integral do diff desde o fechamento da FASE 4, validação da fronteira temporal, verificação individual das dez features, CI pré-merge, CI do PR, merge funcional, CI pós-merge e persistência da memória de fechamento.

### Escopo implementado
- primitive point-in-time `StorageProvider.get_candles_as_of(session_id, as_of)`;
- especificação funcional canônica em `docs/market_features.md`;
- direção do candle;
- amplitude do candle;
- retorno simples close-to-close;
- volatilidade simples populacional;
- HH — Higher High;
- HL — Higher Low;
- LH — Lower High;
- LL — Lower Low;
- tendência estrutural básica;
- lateralização estrutural básica.

### Fronteira temporal e anti-future-leakage
A fronteira validada é:

```text
Temporal Memory
→ get_candles_as_of(session_id, as_of)
→ candles conhecidos naquele instante
→ Market Features
```

Foi comprovado que:
- `as_of` deve ser timezone-aware e é normalizado para UTC;
- a leitura histórica usa snapshots associados a observações com `Observation.timestamp <= as_of`;
- para cada candle, o snapshot mais recente conhecido no corte é escolhido deterministicamente;
- snapshots posteriores e o estado canônico futuro não alteram leituras históricas anteriores;
- lacunas não são preenchidas e janelas contam apenas candles elegíveis;
- `FeatureEngine` não consulta `ReplaySource`, Ground Truth ou storage por conta própria;
- nenhum future leakage foi introduzido.

### Política de candle aberto validada
- direção: alvo aberto permitido;
- amplitude: alvo aberto permitido;
- retorno: alvo aberto permitido, predecessor precisa estar fechado;
- volatilidade: somente candles fechados;
- HH/HL/LH/LL: ambos os candles fechados;
- tendência: somente candles fechados;
- lateralização: somente candles fechados.

### Política numérica validada
- resultados numéricos derivados usam `Decimal`;
- não há conversão para `float` nos cálculos de features;
- divisões e raiz quadrada que exigem contexto controlado usam `localcontext()` com precisão 28 e `ROUND_HALF_EVEN`;
- não há `quantize` nos cálculos;
- retorno segue `(close_t - close_prev) / close_prev` e retorna `None` para predecessor com close zero;
- volatilidade usa variância populacional sobre `N-1` retornos e raiz Decimal;
- lateralização calcula `window_range` e `range_ratio` dentro do contexto Decimal local, com teste de regressão contra influência do contexto global.

### Estrutura e lateralização validadas
- HH = `current.high > previous.high`;
- HL = `current.low > previous.low`;
- LH = `current.high < previous.high`;
- LL = `current.low < previous.low`;
- igualdade estrutural retorna `False`, não `None`;
- combinações high × low são independentes, inclusive `HH=True` com `LL=True`;
- tendência básica exige unanimidade de todos os pares: todos HH+HL → `RISING_STRUCTURE`; todos LH+LL → `FALLING_STRUCTURE`; qualquer outro caso → `MIXED_STRUCTURE`;
- `BasicTrend` possui somente `RISING_STRUCTURE`, `FALLING_STRUCTURE` e `MIXED_STRUCTURE`;
- lateralização usa os últimos N fechados, `basic_trend(window, N-1)`, range `max(high)-min(low)`, referência `abs(close_1)` e retorna `True` somente para `MIXED_STRUCTURE` com `range_ratio <= T`.

### Referências técnicas e integração
- branch funcional: `phase-5-market-features-mvp`;
- HEAD final da branch antes do PR: `c3d6991a78b92d114df9cafb14bf8586d9d41320`;
- CI final da branch: run `#120` / `31464324474` — SUCCESS;
- PR `#8 — feat: complete Phase 5 Market Features MVP` — merged;
- CI do PR: run `#121` / `31465714858` — SUCCESS;
- merge funcional em `main`: `c276b966738abd65ac6c0658e5a9771d558fdb29`;
- CI pós-merge: run `#122` / `31465857520` — SUCCESS.

O HEAD documental final e seu CI são registrados na Issue Mestra #1 após a execução do CI do commit de fechamento, evitando referência recursiva desatualizada dentro de um arquivo versionado.

### Testes e gates
No CI pós-merge do SHA funcional:
- `ruff check app` — SUCCESS;
- `pytest -q` — `137 passed, 34 skipped`;
- PostgreSQL real para persistência FASE 4 + point-in-time FASE 5 — `34 passed`;
- migrations Alembic `upgrade head` — SUCCESS;
- `downgrade base` seguido de novo `upgrade head` — SUCCESS;
- `npm run build` — SUCCESS;
- Docker Compose completo — SUCCESS;
- backend health — `{"status":"ok"}`;
- frontend — SUCCESS;
- governance-memory — SUCCESS.

A execução foi reproduzida pelo GitHub Actions porque não havia checkout local disponível neste ambiente; por isso o worktree local permaneceu `UNKNOWN` e não foi inferido a partir do checkout limpo do CI.

### Revisão de escopo
A FASE 5 não implementou:
- `AnalysisEngine`;
- `UP`, `DOWN`, `SIDEWAYS` ou `UNCERTAIN` como estados de análise;
- previsão ou sinais;
- Outcome Evaluation;
- Dashboard;
- execução real ou integração com corretoras;
- qualquer funcionalidade da FASE 6+.

A lateralização da FASE 5 permanece uma feature booleana e não equivale ao estado `SIDEWAYS` da FASE 6.

### Arquitetura
`FeatureEngine` permanece domínio puro e não depende de SQLAlchemy, psycopg, `app.infrastructure`, PostgreSQL, ReplaySource ou Ground Truth. A primitive point-in-time está no contrato/storage anterior aos cálculos; os métodos de feature não fazem lookup automático de storage.

### Decisões
Nenhuma nova decisão arquitetural material foi necessária durante a FASE 5. As decisões existentes foram suficientes e `docs/DECISIONS.md` permaneceu inalterado.

### Limitações conhecidas
- o v1 permanece restrito ao ambiente/replay controlado;
- métodos de feature recebem candles já recuperados pela fronteira point-in-time e pressupõem a ordem temporal fornecida; não sintetizam gaps;
- janelas contam candles elegíveis, não intervalos temporais preenchidos artificialmente;
- a lateralização é deliberadamente booleana e não realiza classificação do `AnalysisEngine`;
- o aviso de depreciação do Alembic sobre ausência de `path_separator` permanece não bloqueante.

## Próxima missão prevista

### FASE 6 — ANALYSIS LAB MVP

O PASS da FASE 5 **autoriza apenas abrir** a FASE 6 em um novo chat dedicado.

Antes de qualquer planejamento ou implementação da FASE 6:
1. abrir chat dedicado da FASE 6;
2. executar/reproduzir `.agents/skills/chartvision-phase-start/SKILL.md`;
3. recuperar novamente branch, HEAD, CI, Issue Mestra, escopo, roadmap e decisões;
4. produzir novo Phase Brief.

A FASE 6 **não foi iniciada** neste ciclo.

## Estado de implementação por fase

| Fase | Estado | Observação |
|---|---|---|
| 0 — Foundation | ✅ PASS | Baseline validada em CI e Docker |
| 1 — Replay | ✅ PASS | Replay determinístico e gate temporal validados |
| 2 — Visual Observer | ✅ PASS | Captura, detecção visual, confiança e falhas validadas |
| 3 — Candle Reconstruction | ✅ PASS | Pixel→preço, tracking, normalização, OHLC e métricas pós-reconstrução validados |
| 4 — Temporal Memory | ✅ PASS | PostgreSQL temporal, deduplicação, fechamento e rastreabilidade histórica validados |
| 5 — Market Features | ✅ PASS | Point-in-time + especificação + 10 features funcionais validados e integrados |
| 6 — Analysis Lab | ⬜ PENDING | Próxima fase autorizável; exige novo PHASE START em novo chat |
| 7 — Outcome Evaluation | 🔒 BLOCKED | Aguarda PASS da FASE 6 |
| 8 — Dashboard | 🔒 BLOCKED | Aguarda PASS da FASE 7 |

## Regra de retomada

Se um novo chat/agente não souber onde continuar, consultar nesta ordem:
1. `AGENTS.md`;
2. este arquivo;
3. `docs/SCOPE.md`;
4. `docs/ROADMAP.md`;
5. `docs/DECISIONS.md`;
6. `docs/CONTINUITY_PROTOCOL.md`;
7. documentação da fase autorizada;
8. Issue Mestra #1;
9. branch, HEAD, CI, PRs/issues reais.

Nunca inferir progresso apenas por conversa anterior.
