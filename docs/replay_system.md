# Replay System — FASE 1

## Status

**FASE 1 — REPLAY MVP: ✅ PASS**

Implementação integrada pelo PR `#2 — feat: complete Phase 1 Replay MVP`.

## Objetivo

Reproduzir dados OHLC históricos de forma determinística como se estivessem ocorrendo no tempo, alimentando um gráfico controlado sem expor candles futuros antes do instante permitido.

## Implementação final

### `ReplaySource`

Local: `backend/app/infrastructure/replay/replay_source.py`.

Responsabilidades implementadas:
- carregar dataset de referência JSON;
- validar ativo/timeframe/timestamps/OHLC;
- suportar apenas timeframe inicial `1m` no Replay MVP;
- manter relógio virtual explícito, independente do relógio do sistema;
- Start;
- Pause;
- Resume;
- Reset;
- avanço explícito em segundos virtuais;
- liberar somente candles cujo `close_time <= current_time`;
- produzir a mesma sequência para o mesmo dataset/configuração.

Estados do replay:
- `idle`;
- `running`;
- `paused`;
- `stopped`;
- `finished`.

### Dataset de referência

Local: `dataset/sample_replay.json`.

Características:
- ativo artificial `SAMPLE`;
- timeframe `1m`;
- 5 candles OHLC;
- timestamps com timezone;
- dataset pequeno e controlado de propósito para validação determinística.

O dataset é empacotado no backend Docker sem criar uma cópia funcional divergente.

### API de replay

Local: `backend/app/api/routes/replay.py`.

Endpoints:
- `GET /replay`;
- `POST /replay/start`;
- `POST /replay/pause`;
- `POST /replay/resume`;
- `POST /replay/reset`;
- `POST /replay/advance?seconds=N`.

A resposta da API contém somente `visible_candles`; portanto o consumidor não recebe o conjunto futuro do dataset.

### `ChartRenderer`

Local: `frontend/src/components/ChartRenderer.tsx`.

Responsabilidades implementadas:
- consumir somente candles liberados pela API de replay;
- renderizar candles em gráfico controlado;
- usar tema, grid e cores de candles conhecidos;
- não conter lógica de análise;
- não implementar captura ou visão computacional.

### Controles no frontend

Local: `frontend/src/app/App.tsx`.

Controles:
- Start;
- Pause;
- Resume;
- Reset.

Quando o replay está `running`, a interface solicita avanços de 60 segundos virtuais. O intervalo real de interface serve apenas para acelerar a demonstração; a autoridade temporal permanece no relógio virtual do backend.

## Separação arquitetural

```text
Dataset
   ↓
ReplaySource
   ├────────► Ground Truth disponível para avaliação futura
   ↓
API — somente estado permitido
   ↓
ChartRenderer
   ↓
Imagem do gráfico
```

A FASE 1 não implementa o leitor visual. A futura FASE 2 deverá observar somente a imagem do gráfico e não poderá acessar os OHLC verdadeiros para reconstrução.

## Testes executados

Backend:
- `ruff check app` — PASS;
- `pytest -q` — **8 passed**.

Testes específicos cobrem:
- duas execuções equivalentes produzem a mesma sequência;
- candle futuro continua invisível antes do `close_time`;
- 59 segundos não liberam o primeiro candle e +1 segundo libera exatamente o primeiro;
- Pause congela relógio virtual e posição;
- Resume continua do mesmo ponto;
- Reset volta ao estado inicial;
- replay após Reset reproduz a mesma sequência;
- API mantém determinismo e gate de dados futuros.

Frontend:
- `npm run build` — PASS.

Stack:
- Docker Compose build/start — PASS;
- health check backend — PASS;
- frontend servido — PASS.

## Evidência GitHub

- branch: `phase-1-replay-mvp`;
- HEAD técnico: `f335a35bbd028e4e8050d995fea8b4c5a907a0a5`;
- PR: `#2`;
- merge em `main`: `821bce313295701fd69cd1925fa9f4a3726cb731`;
- CI técnico run `#28` / `31373691602` — SUCCESS;
- CI de PR run `#29` / `31374069253` — SUCCESS;
- CI pós-merge run `#30` / `31374254176` — SUCCESS.

Durante o desenvolvimento, o run `#26` falhou em `foundation-docker` porque o dataset raiz não estava no contexto de build do backend. A correção foi aplicada no commit `1c981864e77a9da089733ab726fd1f1dff50f624`, alterando o contexto Docker para empacotar o dataset canônico. Os runs seguintes passaram integralmente.

## Critérios de aceite — resultado

- [x] mesmo dataset gera exatamente a mesma sequência em execuções repetidas;
- [x] Start funciona;
- [x] Pause congela progressão;
- [x] Resume continua do mesmo ponto;
- [x] Reset volta ao estado inicial;
- [x] relógio de replay é determinístico;
- [x] nenhum componente de visão foi implementado;
- [x] nenhum candle futuro é exposto antes do instante permitido;
- [x] testes automatizados passam;
- [x] frontend build passa;
- [x] stack Docker passa;
- [x] CI passa.

## Fora do escopo preservado

Não foram implementados:
- OpenCV funcional para a fase;
- captura visual;
- OCR;
- reconstrução de candles por imagem;
- memória temporal funcional da FASE 4;
- market features;
- AnalysisEngine;
- OutcomeEvaluator;
- integrações externas;
- execução de ordens ou dinheiro real.

## Limitações conhecidas

1. Dataset pequeno/artificial, suficiente para o cenário de referência da FASE 1.
2. Estado do replay em memória e de sessão única; persistência pertence à FASE 4.
3. O renderer prioriza simplicidade do MVP, não otimização para datasets grandes.
4. Nenhuma observação visual é realizada ainda; isso pertence exclusivamente à FASE 2.

## Handoff

A FASE 1 entrega um gráfico controlado e determinístico que pode servir como fonte visual para a FASE 2.

A próxima fase **pode ser aberta**, mas não é iniciada por este documento. A FASE 2 deve começar em novo chat/sessão e executar `chartvision-phase-start` antes de qualquer implementação.
