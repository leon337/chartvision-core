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

## Regras arquiteturais obrigatórias

1. domínio não depende de infraestrutura;
2. fonte do gráfico não invade o núcleo;
3. visão não acessa Ground Truth;
4. frame não é candle;
5. baixa confiança é um estado válido;
6. dados ausentes não são inventados;
7. AnalysisEngine não acessa futuro;
8. OutcomeEvaluator não altera análise original;
9. uma fase não antecipa componentes da fase seguinte sem necessidade estrutural explícita;
10. simplicidade prevalece sobre abstração prematura.

## Stack congelada do v1

- Backend: Python + FastAPI
- Frontend: React + TypeScript + Vite
- Banco: PostgreSQL
- Visão: OpenCV
- Orquestração local/CI: Docker Compose
- Gráfico controlado: TradingView Lightweight Charts ou substituto compatível aprovado sem violar os contratos

Não adicionar Redis, banco vetorial ou TimescaleDB no v1 sem decisão registrada.