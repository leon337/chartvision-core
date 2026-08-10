# ChartVision Core — Estado Atual

> Este é o ponto de retomada operacional do projeto.
>
> Sempre ler este arquivo antes de iniciar uma nova missão.

## Estado atual

- **Versão de planejamento:** v1 congelado
- **Fase atual concluída:** FASE 1 — REPLAY MVP
- **Status:** ✅ PASS
- **Próxima fase autorizável:** FASE 2 — VISUAL OBSERVER MVP
- **Fases posteriores:** bloqueadas até PASS sequencial
- **Issue mestra:** `#1 — MASTER — ChartVision Core v1 Roadmap`
- **Modelo de trabalho:** um chat dedicado por fase + GitHub como memória oficial

## Evidência da FASE 1

A FASE 1 implementou exclusivamente:
- `ReplaySource` com relógio virtual explícito e determinístico;
- dataset OHLC de referência controlado, com um ativo e timeframe de 1 minuto;
- liberação de candles somente quando o `close_time` é alcançado;
- API de replay com Start, Pause, Resume, Reset e avanço explícito;
- `ChartRenderer` controlado com Lightweight Charts;
- controles de replay no frontend;
- empacotamento do dataset canônico na stack Docker.

Referências técnicas:
- branch de implementação: `phase-1-replay-mvp`;
- PR: `#2 — feat: complete Phase 1 Replay MVP`;
- HEAD técnico antes do merge: `f335a35bbd028e4e8050d995fea8b4c5a907a0a5`;
- merge em `main`: `821bce313295701fd69cd1925fa9f4a3726cb731`;
- CI do HEAD técnico: run `#28` / `31373691602` — SUCCESS;
- CI do PR: run `#29` / `31374069253` — SUCCESS;
- CI pós-merge em `main`: run `#30` / `31374254176` — SUCCESS.

Testes/evidências:
- `ruff check app` — PASS;
- `pytest -q` — 8 testes aprovados;
- `npm run build` — PASS;
- stack Docker completa — PASS;
- teste automatizado prova sequência idêntica para execuções equivalentes;
- teste automatizado prova que 59 segundos não liberam o primeiro candle e que o candle só aparece ao atingir seu `close_time`;
- testes cobrem Pause, Resume e Reset;
- API preserva o mesmo gate temporal do `ReplaySource`.

## Limitações conhecidas da FASE 1

- o dataset de referência é intencionalmente pequeno e artificial, adequado ao laboratório determinístico inicial;
- o estado do replay permanece em memória e representa uma única sessão controlada; persistência temporal pertence à FASE 4;
- o frontend usa ritmo visual acelerado para solicitar avanços de 60 segundos virtuais, mas o relógio autoritativo é o relógio virtual do backend;
- não existe captura, OpenCV, OCR ou reconstrução visual nesta fase, por desenho do roadmap.

## Próxima missão prevista

### FASE 2 — VISUAL OBSERVER MVP

A FASE 2 está autorizada a ser **aberta em novo chat dedicado**, mas não foi iniciada por este fechamento.

Antes de qualquer planejamento ou implementação da FASE 2:
1. abrir o chat dedicado da FASE 2;
2. executar/reproduzir `chartvision-phase-start`;
3. recuperar novamente branch, HEAD, CI, Issue Mestra, escopo, roadmap e decisões.

Escopo da FASE 2 permanece o definido em `docs/ROADMAP.md` e `docs/vision_pipeline.md`.

## Estado de implementação por fase

| Fase | Estado | Observação |
|---|---|---|
| 0 — Foundation | ✅ PASS | Baseline validada em CI e Docker |
| 1 — Replay | ✅ PASS | Replay determinístico, controles, renderer e gate temporal validados |
| 2 — Visual Observer | ⬜ PENDING | Próxima fase autorizável; exige novo PHASE START |
| 3 — Candle Reconstruction | 🔒 BLOCKED | Aguarda FASE 2 |
| 4 — Temporal Memory | 🔒 BLOCKED | Aguarda FASE 3 |
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
