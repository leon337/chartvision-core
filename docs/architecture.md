# ChartVision Core — Arquitetura Canônica

## Princípio central

O núcleo deve ser independente da origem do gráfico.

```text
                 FONTES
                   │
        ┌──────────┼──────────┐
        │          │          │
      Replay     Futuras    Arquivos
                  fontes     históricos
        │          │          │
        └──────────┼──────────┘
                   ▼
              ChartSource
                   ▼
              Renderer
                   ▼
                 IMAGEM
                   ▼
            ChartObserver
                   ▼
              Normalizer
                   ▼
        ┌───────────────────┐
        │  CHARTVISION CORE │
        └───────────────────┘
                   │
      ┌────────────┼────────────┐
      ▼            ▼            ▼
TemporalMemory FeatureEngine AnalysisEngine
      │            │            │
      └────────────┼────────────┘
                   ▼
           OutcomeEvaluator
                   ▼
                Metrics
```

## Camadas

### `domain`
Regras, modelos e contratos puros.

O domínio não depende de FastAPI, OpenCV, PostgreSQL ou React.

### `infrastructure`
Implementações técnicas:
- PostgreSQL;
- OpenCV;
- OCR futuro;
- captura;
- implementações concretas de providers.

### `api`
Interface HTTP do backend.

### `frontend`
Interface de replay, observação e auditoria.

## Contratos principais

### `ChartSource`
Abstrai a origem temporal do gráfico.

Implementação v1:
- `ReplaySource`.

Futuras implementações exigem novo escopo.

### `VisionProvider`
Abstrai o processamento visual.

### `StorageProvider`
Abstrai persistência.

### `GroundTruthProvider`
Contrato exclusivo da camada de avaliação posterior.

Na FASE 7, deve fornecer somente a janela Ground Truth necessária para avaliar uma `Analysis` já persistida, respeitando `Analysis.timestamp`, `evaluation_as_of` e o horizonte configurado.

Ele pode ser implementado por um adapter do replay controlado, mas:

- não pode ser consumido por `AnalysisEngine`;
- não pode ser consumido por `AnalysisLabService`;
- não pode ser consumido pelo pipeline visual;
- não transforma Ground Truth em entrada da análise histórica.

O contrato detalhado fica em `docs/outcome_evaluation.md`.

### `OCRProvider`
Contrato previsto para leitura textual quando necessário. Não precisa ser antecipado se a fase não exigir.

### `AnalysisProvider`
Contrato previsto para classificação experimental. Não deve ser implementado antes da FASE 6.

## Ground Truth

O `ReplaySource` conhece os OHLC reais.

O leitor visual não pode acessá-los.

```text
ReplaySource
   │
   ├──────────────► Ground Truth Store
   │                       │
   │                       └────────► GroundTruthProvider
   │                                      │
   │                                      ▼
   │                              Outcome Evaluation
   │
   ▼
ChartRenderer
   │
   ▼
Pixels
   │
   ▼
Vision Pipeline
   │
   ▼
Reconstructed Candle
   │
   └──────────────► comparação posterior com Ground Truth
```

A fronteira adicional da FASE 7 é:

```text
Analysis(T)
   │
   │ imutável
   ▼
OutcomeEvaluationService
   │
   ├── Analysis persistida
   └── GroundTruthProvider → somente janela futura autorizada
            │
            ▼
      OutcomeEvaluator
            │
            ▼
         Outcome
```

Ground Truth posterior pode produzir Outcome, mas nunca alterar `Analysis(T)`.

## Pipeline visual planejado

```text
CaptureService
      ↓
ChartDetector
      ↓
CandleDetector
      ↓
PriceMapper
      ↓
ChartTracker
      ↓
Normalizer
```

Cada componente possui responsabilidade isolada.

## Persistência planejada

Fluxo lógico:

```text
sessions
   ↓
frames
   ↓
observations
   ↓
candles
   ↓
features
   ↓
analyses
   ↓
outcomes
```

Toda entidade temporal deve possuir timestamp e rastreabilidade adequada.

No MVP da FASE 7, métricas agregadas são derivadas de `Analysis + Outcome`; não é necessária tabela persistente de métricas sem nova decisão.

## Regras arquiteturais obrigatórias

1. domínio não depende de infraestrutura;
2. fonte do gráfico não invade o núcleo;
3. visão não acessa Ground Truth;
4. frame não é candle;
5. baixa confiança é um estado válido;
6. dados ausentes não são inventados;
7. AnalysisEngine não acessa futuro;
8. OutcomeEvaluator não altera análise original;
9. Ground Truth posterior entra somente pela camada de avaliação autorizada;
10. OutcomeEvaluator permanece desacoplado de ReplaySource e infraestrutura;
11. uma fase não antecipa componentes da fase seguinte sem necessidade estrutural explícita;
12. simplicidade prevalece sobre abstração prematura.

## Stack congelada do v1

- Backend: Python + FastAPI
- Frontend: React + TypeScript + Vite
- Banco: PostgreSQL
- Visão: OpenCV
- Orquestração local/CI: Docker Compose
- Gráfico controlado: TradingView Lightweight Charts ou substituto compatível aprovado sem violar os contratos

Não adicionar Redis, banco vetorial ou TimescaleDB no v1 sem decisão registrada.
