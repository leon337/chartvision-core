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

Quando o replay está `running`, a interface solicita avanços de 60 segundos virtuais. O intervalo real de interface serve apenas para acelerar a demonstração; a autoridade temporal operacional permanece no relógio virtual do backend.

## Semântica de cursor e reset para consumidores experimentais posteriores

A FASE 1 aprovou `Reset` como operação de reprodução. O comportamento funcional vigente do `ReplaySource.reset()` é:

```text
_position = 0
_current_time = None
_status = IDLE
```

Portanto o relógio/cursor operacional atual do replay é **rebobinável**.

Esse comportamento continua correto e **não é alterado retroativamente** por documentação da FASE 7.

A distinção obrigatória para consumidores experimentais posteriores é:

```text
replay_cursor_time
=
posição operacional corrente
pode rebobinar com reset
```

versus:

```text
session_exposure_watermark
=
maior instante lógico já exposto
na mesma sessão/experimento
não rebobina com reset
```

Consequência:

```text
reset
→ pode provar que o cursor voltou
X→ não prova que o futuro nunca foi visto antes
```

Outcome Evaluation não pode usar `_current_time`, `ReplaySnapshot.current_time` ou posição corrente rebobinada como prova exclusiva de precommit experimental.

O contrato futuro da FASE 7 deve manter um exposure watermark separado e monotonicamente não decrescente por sessão. Esse estado não faz parte da implementação concluída da FASE 1 e **não é implementado por esta atualização documental**.

Exemplo normativo para consumidores posteriores:

```text
sessão avança até 10:30
replay_cursor_time = 10:30
session_exposure_watermark = 10:30

reset
replay_cursor_time = início / None
session_exposure_watermark = 10:30

replay avança novamente até 10:15
replay_cursor_time = 10:15
session_exposure_watermark = 10:30

replay avança até 10:45
replay_cursor_time = 10:45
session_exposure_watermark = 10:45
```

Reset da mesma reprodução não deve ser reinterpretado silenciosamente como nova sessão/experimento para Outcome Evaluation. Mudança de target experimental no MVP continua exigindo nova sessão/experimento conforme `docs/outcome_evaluation.md` e D-019/D-020.

O exposure watermark contém somente a fronteira temporal já exposta. Ele não fornece OHLC ao AnalysisEngine, FeatureEngine ou pipeline visual e não modifica o gate de Ground Truth da FASE 1.

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

Para fases experimentais posteriores, a posição corrente do replay e a memória de exposição são responsabilidades semanticamente distintas; isso não muda o fluxo visual acima.

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

Esses testes continuam sendo a autoridade para a semântica funcional da FASE 1. A futura FASE 7 deverá adicionar testes próprios para garantir que seu exposure watermark não diminui quando esses resets válidos da FASE 1 ocorrem.

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

A separação posterior entre cursor rebobinável e exposure watermark não modifica nem invalida esses critérios; ela impede apenas que uma fase posterior atribua ao cursor uma semântica experimental que ele nunca teve.

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
- exposure watermark persistente;
- OutcomeEvaluationPolicy;
- integrações externas;
- execução de ordens ou dinheiro real.

## Limitações conhecidas

1. Dataset pequeno/artificial, suficiente para o cenário de referência da FASE 1.
2. Estado do replay em memória e de sessão única; persistência pertence às fases posteriores conforme seus contratos.
3. O renderer prioriza simplicidade do MVP, não otimização para datasets grandes.
4. Nenhuma observação visual é realizada ainda; isso pertence exclusivamente à FASE 2.
5. O cursor/`current_time` da FASE 1 é intencionalmente rebobinável por Reset e não deve ser usado por fases posteriores como prova histórica de não exposição.

## Handoff

A FASE 1 entrega um gráfico controlado e determinístico que pode servir como fonte visual para a FASE 2.

A semântica funcional da FASE 1 permanece fechada/PASS. Consumidores posteriores que precisem auditar exposição através de resets devem manter estado próprio não rebobinável conforme a decisão de sua fase, sem alterar `ReplaySource.reset()` retroativamente.

A próxima fase **pode ser aberta**, mas não é iniciada por este documento. A FASE 2 deve começar em novo chat/sessão e executar `chartvision-phase-start` antes de qualquer implementação.
