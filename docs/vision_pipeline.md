# Vision Pipeline — FASES 2 e 3

## Objetivo

Observar o gráfico como imagem e reconstruir candles sem acessar os OHLC verdadeiros usados pelo replay.

## Pipeline planejado

```text
ChartRenderer
    ↓
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
    ↓
NormalizedCandle
```

## FASE 2 — Visual Observer

### `CaptureService`
- capturar a região do gráfico;
- intervalo padrão inicial: 5 segundos;
- identificar mudanças de frame;
- gerar referência/hash de captura.

### `ChartDetector`
- localizar área útil do gráfico;
- localizar região de candles;
- localizar eixo de preço quando aplicável;
- retornar confiança.

### `CandleDetector`
Detectar visualmente:
- posição X;
- corpo;
- pavio superior;
- pavio inferior;
- direção visual;
- largura;
- confiança.

Não converter pixels em preço neste componente.

## FASE 3 — Candle Reconstruction

### `PriceMapper`
Converter coordenada vertical em preço usando a escala detectada.

### `ChartTracker`
- manter identidade de candles entre frames;
- atualizar candle ainda aberto;
- reconhecer novo candle;
- reconhecer deslocamento horizontal;
- detectar fechamento;
- impedir duplicação.

### `Normalizer`
Converter representação visual para o modelo canônico de candle.

## Regra crítica

**Frame não é candle.**

Várias capturas podem representar estados sucessivos do mesmo candle de 1 minuto.

## Ground Truth

Ground Truth só pode ser usado depois da reconstrução para medir erro. Nunca pode alimentar os detectores.

## Métricas previstas

- Open error;
- High error;
- Low error;
- Close error;
- candle detection rate;
- direction accuracy;
- duplicate rate;
- missing candle rate.

## Estados de falha válidos

- `CHART_NOT_FOUND`;
- `LOW_IMAGE_QUALITY`;
- `PRICE_SCALE_NOT_FOUND`;
- `CANDLE_DETECTION_FAILED`;
- `TRACKING_LOST`.

O sistema deve preferir falhar explicitamente a fabricar dados.