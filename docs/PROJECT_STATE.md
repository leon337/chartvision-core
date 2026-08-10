# ChartVision Core — Estado Atual

> Este é o ponto de retomada operacional do projeto.
>
> Sempre ler este arquivo antes de iniciar uma nova missão.

## Estado atual

- **Versão de planejamento:** v1 congelado
- **Fase atual concluída:** FASE 3 — CANDLE RECONSTRUCTION MVP
- **Status:** ✅ PASS
- **Últimos PASS sequenciais:** FASE 0 — FOUNDATION; FASE 1 — REPLAY MVP; FASE 2 — VISUAL OBSERVER MVP; FASE 3 — CANDLE RECONSTRUCTION MVP
- **Próxima fase autorizável:** FASE 4 — TEMPORAL MEMORY MVP
- **Fases posteriores:** bloqueadas até PASS sequencial
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
- `ReconstructionEvaluator` separado para comparação **posterior** com Ground Truth;
- métricas Open/High/Low/Close error, candle detection rate, direction accuracy, duplicate rate e missing candle rate.

### Referências técnicas
- branch: `phase-3-candle-reconstruction-mvp`;
- HEAD técnico: `b5dd7abecc8402ff825204b2bfe32cd158d2e483`;
- PR: `#6 — feat: complete Phase 3 Candle Reconstruction MVP` — merged;
- merge funcional em `main`: `58f202e6ca1bfea3bf6f1f08a737a78bd3e3b71c`;
- CI técnico final da branch: run `#42` / `31419351907` — SUCCESS;
- CI do PR: run `#43` / `31419606685` — SUCCESS;
- CI pós-merge: run `#44` / `31419758543` — SUCCESS.

### Testes e critérios
Suíte específica da FASE 3 no diretório `backend`:

```text
PYTHONPATH=. pytest -q app/tests/unit/test_price_mapper.py app/tests/unit/test_price_scale_reader.py app/tests/unit/test_chart_tracker.py app/tests/unit/test_normalizer.py app/tests/unit/test_reconstruction_evaluator.py app/tests/unit/test_phase3_architecture.py app/tests/integration/test_candle_reconstruction.py
```

Resultado: `27 passed`.

No CI:
- `ruff check app` — SUCCESS;
- `pytest -q` — SUCCESS;
- `npm run build` — SUCCESS;
- stack Docker completa — SUCCESS.

A integração controlada comprova:
- múltiplos frames atualizando o mesmo candle aberto sem duplicação;
- novo candle fechando o anterior;
- deslocamento horizontal de `-70 px`;
- três candles fechados reconstruídos;
- erros de Open/High/Low/Close iguais a `0` no cenário de referência;
- detection rate `1.0`;
- direction accuracy `1.0`;
- duplicate rate `0.0`;
- missing candle rate `0.0`.

Teste arquitetural comprova que mapping/tracking/normalização/pipeline não importam replay, Ground Truth ou `ChartSource`. Ground Truth aparece somente no avaliador pós-reconstrução.

### Limitações conhecidas da FASE 3
- leitura numérica da escala é calibrada ao renderer/fixture controlado do v1, não a plataformas externas;
- detector e leitura continuam dependentes do tema/tamanho/cores/fonte controlados do cenário v1;
- estado de tracking e reconstrução permanece em memória de processo;
- persistência temporal e rastreabilidade histórica pertencem à FASE 4;
- métricas perfeitas registradas são apenas evidência do cenário controlado, não threshold universal.

## Próxima missão prevista

### FASE 4 — TEMPORAL MEMORY MVP

O PASS da FASE 3 **autoriza apenas abrir** a FASE 4 em um novo chat dedicado.

Antes de qualquer planejamento ou implementação da FASE 4:
1. abrir chat dedicado da FASE 4;
2. executar/reproduzir `.agents/skills/chartvision-phase-start/SKILL.md`;
3. recuperar novamente branch, HEAD, CI, Issue Mestra, escopo, roadmap e decisões;
4. produzir novo Phase Brief.

A FASE 4 **não foi iniciada** neste ciclo.

## Estado de implementação por fase

| Fase | Estado | Observação |
|---|---|---|
| 0 — Foundation | ✅ PASS | Baseline validada em CI e Docker |
| 1 — Replay | ✅ PASS | Replay determinístico e gate temporal validados |
| 2 — Visual Observer | ✅ PASS | Captura, detecção visual, confiança e falhas validadas |
| 3 — Candle Reconstruction | ✅ PASS | Pixel→preço, tracking, normalização, OHLC e métricas pós-reconstrução validados |
| 4 — Temporal Memory | ⬜ PENDING | Próxima fase autorizável; exige novo PHASE START |
| 5 — Market Features | 🔒 BLOCKED | Aguarda FASE 4 |
| 6 — Analysis Lab | 🔒 BLOCKED | Aguarda FASE 5 |
| 7 — Outcome Evaluation | 🔒 BLOCKED | Aguarda FASE 6 |
| 8 — Dashboard | 🔒 BLOCKED | Aguarda FASE 7 |

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
