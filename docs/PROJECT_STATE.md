# ChartVision Core — Estado Atual

> Este é o ponto de retomada operacional do projeto.
>
> Sempre ler este arquivo antes de iniciar uma nova missão.

## Estado atual

- **Versão de planejamento:** v1 congelado
- **Última fase formalmente concluída:** FASE 4 — TEMPORAL MEMORY MVP
- **Último status formal:** ✅ PASS
- **Fase atualmente em desenvolvimento:** FASE 5 — MARKET FEATURES MVP
- **Status operacional atual:** 🟡 IN PROGRESS
- **Branch ativa:** `phase-5-market-features-mvp`
- **Último incremento técnico revalidado:** `1915369f123fed9109e3ee9155be777f63672582`
- **CI técnico revalidado:** run `#116` / `31463891443` — SUCCESS
- **Último HEAD operacional validado:** `07128e7cf6f77e3f9e3d99bc15eade6725b8fb4e`
- **CI final do incremento:** run `#118` / `31464104850` — SUCCESS
- **Últimos PASS sequenciais:** FASE 0 — FOUNDATION; FASE 1 — REPLAY MVP; FASE 2 — VISUAL OBSERVER MVP; FASE 3 — CANDLE RECONSTRUCTION MVP; FASE 4 — TEMPORAL MEMORY MVP
- **Próxima fase:** FASE 6 — ANALYSIS LAB MVP — bloqueada até `PHASE_CLOSE = PASS` da FASE 5
- **Issue mestra:** `#1 — MASTER — ChartVision Core v1 Roadmap`
- **Modelo de trabalho:** um chat dedicado por fase + GitHub como memória oficial

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
- suíte backend sem variável de PostgreSQL: `47 passed, 31 skipped`; os 31 skips são os testes PostgreSQL executados no job dedicado;
- testes reais contra PostgreSQL: `31 passed`;
- migrations Alembic `upgrade head` até `0004` — SUCCESS;
- `downgrade base` seguido de novo `upgrade head` — SUCCESS;
- `npm run build` — SUCCESS;
- stack Docker completa e health checks — SUCCESS.

Critérios oficiais comprovados:
1. **Replays repetidos não corrompem dados** — teste PostgreSQL repete o histórico lógico e comprova que o estado canônico não regride, preservando snapshots auditáveis.
2. **Candles não são duplicados dentro da mesma sessão** — chave primária `(session_id, open_time)` e teste de replay repetido mantêm uma única linha canônica.
3. **Dados históricos não são sobrescritos silenciosamente** — snapshots por observação são imutáveis; divergência no mesmo timestamp, regressão temporal e alteração pós-fechamento geram conflito explícito.

### Revisão de escopo no fechamento da FASE 4
Nenhum cálculo de `MarketFeatures` havia sido implementado no fechamento da FASE 4. Direção, amplitude, retorno, volatilidade, HH/HL/LH/LL, tendência e lateralização permaneceram reservados à FASE 5 naquele fechamento.

### Decisões
Nenhuma nova decisão arquitetural foi necessária para o fechamento. As decisões já registradas para banco temporal estruturado e PostgreSQL permanecem suficientes; `docs/DECISIONS.md` não foi alterado.

### Limitações conhecidas
- o v1 permanece restrito ao ambiente/replay controlado;
- persistência preserva dados reconstruídos pela visão, sem alterar a separação de Ground Truth;
- o aviso de depreciação do Alembic sobre ausência de `path_separator` é não bloqueante e não altera a funcionalidade da FASE 4.

## FASE 5 — MARKET FEATURES MVP — IN PROGRESS

A FASE 5 foi aberta após o PASS formal da FASE 4 e seu lifecycle de início foi executado/revalidado. O fechamento formal da FASE 5 ainda não ocorreu.

### Estado técnico revalidado
- branch ativa: `phase-5-market-features-mvp`;
- último incremento técnico aprovado: `1915369f123fed9109e3ee9155be777f63672582`;
- CI desse incremento: run `#116` / `31463891443` — SUCCESS;
- HEAD operacional final do incremento: `07128e7cf6f77e3f9e3d99bc15eade6725b8fb4e`;
- CI final do incremento: run `#118` / `31464104850` — SUCCESS;
- nenhuma PR aberta da FASE 5 no momento da revalidação;
- nenhuma branch concorrente `phase-5` identificada.

### Progresso técnico já implementado
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

### Trabalho ainda pendente na FASE 5
- revisão independente do incremento final;
- verificação formal de fechamento por `.agents/skills/chartvision-phase-close/SKILL.md`, somente após nova autorização explícita.

Não há feature funcional pendente no escopo congelado da FASE 5. Isso não equivale a `PASS`: o lifecycle formal de fechamento ainda não foi executado.

### Limite de progressão
A FASE 5 permanece **IN PROGRESS**. A FASE 6 — ANALYSIS LAB MVP permanece bloqueada até revisão final, validações de fechamento, atualização de memória exigida pelo lifecycle e `PHASE_CLOSE = PASS` da FASE 5.

## Estado de implementação por fase

| Fase | Estado | Observação |
|---|---|---|
| 0 — Foundation | ✅ PASS | Baseline validada em CI e Docker |
| 1 — Replay | ✅ PASS | Replay determinístico e gate temporal validados |
| 2 — Visual Observer | ✅ PASS | Captura, detecção visual, confiança e falhas validadas |
| 3 — Candle Reconstruction | ✅ PASS | Pixel→preço, tracking, normalização, OHLC e métricas pós-reconstrução validados |
| 4 — Temporal Memory | ✅ PASS | PostgreSQL temporal, deduplicação, fechamento e rastreabilidade histórica validados |
| 5 — Market Features | 🟡 IN PROGRESS | Point-in-time + especificação + 10 features funcionais implementados; fechamento formal pendente |
| 6 — Analysis Lab | 🔒 BLOCKED | Aguarda `PHASE_CLOSE = PASS` da FASE 5 |
| 7 — Outcome Evaluation | 🔒 BLOCKED | Aguarda FASE 6 |
| 8 — Dashboard | 🔒 BLOCKED | Aguarda FASE 7 |

## Próxima ação autorizável na fase atual

O próximo passo é a revisão independente do incremento final e, somente após nova autorização explícita, a verificação formal de fechamento da FASE 5 por `chartvision-phase-close`. A FASE 6 não está autorizada enquanto esse fechamento não resultar em `PASS`.

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
