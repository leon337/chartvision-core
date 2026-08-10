# Vision Pipeline — FASES 2 e 3

## Objetivo

Observar o gráfico como imagem e reconstruir candles sem acessar os OHLC verdadeiros usados pelo replay.

## Estado

- **FASE 2 — Visual Observer MVP:** ✅ PASS
- **FASE 3 — Candle Reconstruction MVP:** ⬜ PENDING

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

## FASE 2 — Visual Observer — ✅ PASS

### `CaptureService`
Implementado para:
- receber bytes da imagem controlada;
- recortar uma região visual opcional;
- manter intervalo padrão inicial de 5 segundos;
- gerar SHA-256 dos pixels da captura;
- preencher o contrato `Frame` com dimensões/hash/referência;
- identificar mudança/não mudança em relação ao frame anterior da mesma sessão.

### `ChartDetector`
Implementado com OpenCV para:
- localizar a área útil do gráfico controlado;
- localizar a região de candles;
- localizar visualmente a região da escala de preço quando presente;
- localizar visualmente o limite da escala de tempo quando presente;
- retornar confiança e qualidade visual;
- retornar `CHART_NOT_FOUND`, `LOW_IMAGE_QUALITY` ou aviso `PRICE_SCALE_NOT_FOUND` quando aplicável.

A localização da escala é somente geométrica. Não existe conversão de coordenada em preço na FASE 2.

### `CandleDetector`
Implementado para detectar visualmente:
- posição X;
- corpo;
- pavio superior;
- pavio inferior;
- direção visual baseada nas cores controladas;
- largura;
- confiança.

Quando os pixels são insuficientes ou nenhum candle é identificável, retorna falha explícita em vez de fabricar dados.

### `OpenCVVisionProvider`
O contrato de observação recebe somente:

```text
observe(image: bytes)
```

Não há argumento, import ou dependência de `ReplaySource`, OHLC verdadeiro ou Ground Truth no pipeline visual da FASE 2.

### Cenário visual de referência
Os testes constroem uma imagem controlada com a mesma paleta visual do `ChartRenderer`, contendo área de gráfico, grid, escala visual e três candles visíveis. A fixture contém somente pixels/elementos visuais; não fornece OHLC ao detector.

### Evidência da FASE 2
- branch: `phase-2-visual-observer-mvp`;
- HEAD técnico: `83d5b8dc7c94fdc472a3049bb30f835454e45d1a`;
- PR: `#3 — feat: complete Phase 2 Visual Observer MVP` — merged;
- merge em `main`: `afc028a6c966ec8be628dee59b9aa432ebd8921c`;
- CI técnico: run `#34` / `31407809004` — SUCCESS;
- CI do PR: run `#35` / `31408022011` — SUCCESS;
- CI pós-merge: run `#36` / `31408244075` — SUCCESS;
- `ruff check app` — PASS;
- `pytest -q` — 19 passed;
- `npm run build` — PASS;
- stack Docker completa — PASS.

### Critérios de aceite comprovados
- visão trabalha estritamente com imagem/pixels e não acessa OHLC/Ground Truth;
- os três candles visíveis do cenário controlado são identificados com geometria, direção e confiança;
- falhas são estados explícitos, sem dados inventados;
- hash e mudança de frame são testados;
- intervalo padrão de captura é 5 segundos;
- `Frame` não é tratado como candle e não existe tracking/reconstrução antecipada.

### Limitações conhecidas
- a heurística inicial é calibrada para o tema/tamanho/cores controlados do v1;
- o estado de comparação de hashes é em memória de processo, não persistência temporal;
- aquisição automatizada de telas de plataformas externas está fora do v1;
- não há OCR obrigatório nesta fase porque o aceite não exige leitura numérica da escala;
- pixel → preço, tracking, normalização, OHLC e deduplicação temporal permanecem fora da FASE 2.

## FASE 3 — Candle Reconstruction — ⬜ PENDING

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

A FASE 3 não foi iniciada neste fechamento. Deve começar em novo chat e executar `chartvision-phase-start` novamente.

## Regra crítica

**Frame não é candle.**

Várias capturas podem representar estados sucessivos do mesmo candle de 1 minuto.

## Ground Truth

Ground Truth só pode ser usado depois da reconstrução para medir erro. Nunca pode alimentar os detectores.

## Métricas previstas para a reconstrução

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
