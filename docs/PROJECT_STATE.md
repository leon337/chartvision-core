# ChartVision Core — Estado Atual

> Este é o ponto de retomada operacional do projeto.
>
> Sempre ler este arquivo antes de iniciar uma nova missão.

## Estado atual

- **Versão de planejamento:** v1 congelado
- **Fase atual concluída:** FASE 2 — VISUAL OBSERVER MVP
- **Status:** ✅ PASS
- **Últimos PASS sequenciais:** FASE 0 — FOUNDATION; FASE 1 — REPLAY MVP; FASE 2 — VISUAL OBSERVER MVP
- **Próxima fase autorizável:** FASE 3 — CANDLE RECONSTRUCTION MVP
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

## Evidência da FASE 2

A FASE 2 implementou exclusivamente observação visual por pixels:
- `CaptureService` com crop de região controlada, hash SHA-256 dos pixels, produção de `Frame`, detecção de mudança e intervalo padrão de 5 segundos;
- contratos visuais para regiões, pavios, candles visuais, confiança, qualidade e estados de falha;
- `ChartDetector` com OpenCV para localizar área útil do gráfico, região de candles e localização visual da escala de preço;
- `CandleDetector` inicial para posição X, corpo, pavio superior/inferior, largura, direção visual e confiança;
- `OpenCVVisionProvider` com entrada exclusivamente `image: bytes`;
- estados explícitos `CHART_NOT_FOUND`, `LOW_IMAGE_QUALITY`, `PRICE_SCALE_NOT_FOUND` e `CANDLE_DETECTION_FAILED`;
- cenário visual controlado de referência sem uso de OHLC/Ground Truth pelo detector.

Referências técnicas:
- branch de implementação: `phase-2-visual-observer-mvp`;
- HEAD técnico: `83d5b8dc7c94fdc472a3049bb30f835454e45d1a`;
- PR: `#3 — feat: complete Phase 2 Visual Observer MVP` — merged;
- merge funcional em `main`: `afc028a6c966ec8be628dee59b9aa432ebd8921c`;
- CI técnico: run `#34` / `31407809004` — SUCCESS;
- CI do PR: run `#35` / `31408022011` — SUCCESS;
- CI pós-merge: run `#36` / `31408244075` — SUCCESS.

Testes/evidências:
- `ruff check app` — PASS;
- `pytest -q` — 19 testes aprovados;
- `npm run build` — PASS;
- stack Docker completa — PASS;
- `CaptureService` testado para crop, hash, frame igual/diferente e gate de 5 segundos;
- `ChartDetector` testado para gráfico válido, gráfico ausente, baixa qualidade e escala de preço ausente;
- `CandleDetector` testado para geometria, direção, pavios, confiança, baixa qualidade e ausência de candles;
- integração identifica 3 candles visíveis no cenário visual de referência;
- teste arquitetural comprova que os módulos visuais não importam replay/`ChartSource` e que `observe` recebe apenas imagem.

Critérios comprovados:
- visão não acessa OHLC do `ReplaySource` nem Ground Truth;
- candles visíveis são identificados no cenário de referência com geometria, direção e confiança;
- falhas de leitura retornam estados explícitos sem fabricar dados;
- captura produz hash e mudança de frame, mantendo intervalo inicial de 5 segundos;
- `Frame` continua separado de candle e nenhuma lógica de tracking/reconstrução foi antecipada.

## Limitações conhecidas da FASE 2

- a detecção inicial é deliberadamente calibrada para o tema, tamanho e cores controlados do v1;
- a fixture de referência é visual/sintética e replica o contrato visual do renderer controlado; generalização para outras fontes não faz parte da FASE 2;
- `CaptureService` recebe bytes de imagem e recorta a região solicitada; automação de navegador/plataforma externa não faz parte do v1;
- o estado usado para comparar hashes de frames é somente memória de processo; persistência temporal pertence à FASE 4;
- não existe conversão pixel → preço;
- `PriceMapper`, `ChartTracker` e `Normalizer` permanecem reservados à FASE 3;
- não existe reconstrução OHLC, identificação aberto/fechado ou deduplicação temporal nesta fase.

## Próxima missão prevista

### FASE 3 — CANDLE RECONSTRUCTION MVP

A FASE 3 está autorizada apenas a ser **aberta em novo chat dedicado** após o fechamento formal da FASE 2.

Antes de qualquer planejamento ou implementação da FASE 3:
1. abrir o chat dedicado da FASE 3;
2. executar/reproduzir `chartvision-phase-start`;
3. recuperar novamente branch, HEAD, CI, Issue Mestra, escopo, roadmap e decisões.

O PASS da FASE 2 não inicia automaticamente a FASE 3.

## Estado de implementação por fase

| Fase | Estado | Observação |
|---|---|---|
| 0 — Foundation | ✅ PASS | Baseline validada em CI e Docker |
| 1 — Replay | ✅ PASS | Replay determinístico, controles, renderer e gate temporal validados |
| 2 — Visual Observer | ✅ PASS | Captura, detecção visual, confiança e falhas explícitas validadas |
| 3 — Candle Reconstruction | ⬜ PENDING | Próxima fase autorizável; exige novo PHASE START |
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
