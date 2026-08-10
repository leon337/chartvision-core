# Vision Pipeline — FASES 2 e 3

## Objetivo

Observar o gráfico como imagem e reconstruir candles sem acessar os OHLC verdadeiros usados pelo replay.

## Estado

- **FASE 2 — Visual Observer MVP:** ✅ PASS
- **FASE 3 — Candle Reconstruction MVP:** ✅ PASS

## Pipeline validado

```text
ChartRenderer
    ↓
CaptureService
    ↓
ChartDetector
    ↓
CandleDetector
    ↓
OpenCVPriceScaleReader
    ↓
PriceMapper
    ↓
ChartTracker
    ↓
Normalizer
    ↓
Candle canônico
```

## FASE 2 — Visual Observer — ✅ PASS

### `CaptureService`
Implementado para receber bytes da imagem controlada, recortar região visual opcional, manter intervalo padrão inicial de 5 segundos, gerar SHA-256 dos pixels, produzir `Frame` e indicar mudança/não mudança em relação ao frame anterior da sessão.

### `ChartDetector`
Implementado com OpenCV para localizar área útil do gráfico, região de candles, região visual da escala de preço e limite visual da escala de tempo, retornando confiança, qualidade e falhas explícitas.

### `CandleDetector`
Detecta posição X, corpo, pavio superior/inferior, direção pelas cores controladas, largura e confiança. Pixels insuficientes ou ausência de candles retornam falha explícita.

### Fronteira da FASE 2
`OpenCVVisionProvider.observe(image: bytes)` recebe somente imagem. Não importa `ReplaySource`, `ChartSource`, OHLC verdadeiro ou Ground Truth.

### Evidência da FASE 2
- branch: `phase-2-visual-observer-mvp`;
- HEAD técnico: `83d5b8dc7c94fdc472a3049bb30f835454e45d1a`;
- PR `#3` — merged;
- merge em `main`: `afc028a6c966ec8be628dee59b9aa432ebd8921c`;
- CI final anterior: run `#37` / `31408563320` — SUCCESS.

## FASE 3 — Candle Reconstruction — ✅ PASS

### `OpenCVPriceScaleReader`
Extrai anchors numéricos da escala **a partir dos pixels da própria imagem controlada**. O leitor usa somente OpenCV já presente na stack e templates de dígitos renderizados para o cenário controlado do v1.

Não recebe OHLC, `ReplaySource`, `ChartSource` ou Ground Truth. Se a escala visual não produzir anchors suficientes, falha explicitamente.

### `PriceMapper`
Implementado para:
- representar `PriceAnchor` com coordenada Y, preço visualmente lido e confiança;
- aceitar múltiplos anchors;
- validar escala ausente, anchors insuficientes, Y duplicado, não monotonicidade e inconsistência de inclinação;
- identificar orientação vertical da escala;
- interpolar `Y → preço` de forma determinística usando `Decimal`;
- não extrapolar além da faixa calibrada;
- produzir confiança de calibração;
- reconstruir preços de corpo/pavios sem qualquer OHLC verdadeiro.

### `ChartTracker`
Implementado para:
- manter identidade temporal do mesmo candle entre múltiplos frames;
- atualizar candle ainda aberto sem criar duplicação;
- reconhecer novo candle;
- marcar fechamento do candle anterior quando o bucket temporal avança;
- reconhecer deslocamento horizontal consistente do gráfico;
- validar espaçamento dos candles;
- retornar `TRACKING_LOST` quando a identidade visual não pode ser preservada.

O estado do tracker é somente memória de processo. Persistência operacional pertence à FASE 4.

### `Normalizer`
Converte `TrackedCandle` em `Candle` canônico, preservando:
- Open, High, Low e Close reconstruídos;
- `open_time` e `close_time`;
- estado aberto/fechado;
- confiança da visão;
- deduplicação temporal limitada à reconstrução, mantendo a observação mais recente da mesma identidade.

OHLC inválido é recusado explicitamente.

### `CandleReconstructionPipeline`
Pipeline stateful da FASE 3:

```text
imagem + Frame
→ OpenCVVisionProvider
→ leitura visual da escala
→ PriceMapper
→ ChartTracker
→ Normalizer
→ Candle canônico
```

Ground Truth não é argumento nem dependência desse pipeline.

### Avaliação pós-reconstrução
`ReconstructionEvaluator` fica separado do pipeline visual e recebe Ground Truth **somente depois** de candles já terem sido reconstruídos.

Métricas implementadas:
- Open error;
- High error;
- Low error;
- Close error;
- candle detection rate;
- direction accuracy;
- duplicate rate;
- missing candle rate.

### Cenário controlado de integração
A integração da FASE 3 utiliza três frames sucessivos e comprova:
- vários frames representando o mesmo candle aberto;
- atualização do candle aberto sem duplicação;
- surgimento de novo candle;
- fechamento do anterior;
- deslocamento horizontal de `-70 px`;
- três candles fechados reconstruídos no cenário de referência;
- Ground Truth aplicado somente após a reconstrução.

No cenário controlado, a avaliação pós-reconstrução resulta em:
- Open error = `0`;
- High error = `0`;
- Low error = `0`;
- Close error = `0`;
- candle detection rate = `1.0`;
- direction accuracy = `1.0`;
- duplicate rate = `0.0`;
- missing candle rate = `0.0`.

Esses valores são evidência do cenário de referência e **não** constituem threshold universal ou promessa de generalização.

### Testes da FASE 3
Suíte específica executada no diretório `backend`:

```text
PYTHONPATH=. pytest -q app/tests/unit/test_price_mapper.py app/tests/unit/test_price_scale_reader.py app/tests/unit/test_chart_tracker.py app/tests/unit/test_normalizer.py app/tests/unit/test_reconstruction_evaluator.py app/tests/unit/test_phase3_architecture.py app/tests/integration/test_candle_reconstruction.py
```

Resultado: `27 passed`.

CI executa adicionalmente:
- `ruff check app` — SUCCESS;
- `pytest -q` — SUCCESS;
- `npm run build` — SUCCESS;
- stack Docker completa — SUCCESS.

### Evidência da FASE 3
- branch: `phase-3-candle-reconstruction-mvp`;
- HEAD técnico: `b5dd7abecc8402ff825204b2bfe32cd158d2e483`;
- PR `#6 — feat: complete Phase 3 Candle Reconstruction MVP` — merged;
- merge em `main`: `58f202e6ca1bfea3bf6f1f08a737a78bd3e3b71c`;
- CI técnico final da branch: run `#42` / `31419351907` — SUCCESS;
- CI do PR: run `#43` / `31419606685` — SUCCESS;
- CI pós-merge: run `#44` / `31419758543` — SUCCESS.

### Critérios de aceite comprovados
- pixel Y é convertido em preço somente a partir da escala visível;
- OHLC é reconstruído a partir de geometria visual + escala;
- múltiplos frames preservam a identidade do mesmo candle;
- candle aberto é atualizado sem duplicação;
- novo candle, fechamento e deslocamento horizontal são reconhecidos no cenário controlado;
- `Normalizer` produz candles canônicos e preserva confiança;
- ausência/insuficiência/inconsistência gera falha explícita;
- Ground Truth não alimenta visão, mapping, tracking ou reconstrução;
- as oito métricas obrigatórias são calculadas somente após a reconstrução;
- o cenário de referência é estável e não apresenta duplicação/candle ausente.

## Regra crítica

**FRAME NÃO É CANDLE.** Várias capturas podem representar estados sucessivos do mesmo candle.

## Ground Truth

Ground Truth só pode ser usado depois da reconstrução para medir erro. Nunca alimenta `ChartDetector`, `CandleDetector`, leitura da escala, `PriceMapper`, `ChartTracker`, `Normalizer` ou `CandleReconstructionPipeline`.

## Estados de falha válidos

- `CHART_NOT_FOUND`;
- `LOW_IMAGE_QUALITY`;
- `PRICE_SCALE_NOT_FOUND`;
- `CANDLE_DETECTION_FAILED`;
- `TRACKING_LOST`.

O sistema prefere falhar explicitamente a fabricar dados.

## Limitações conhecidas após a FASE 3

- leitura dos rótulos da escala é calibrada ao renderer/fixture controlado do v1 e não é OCR genérico para plataformas externas;
- detector visual continua calibrado para tema, dimensões e cores controlados;
- tracking/reconstrução permanecem em memória de processo;
- persistência temporal, rastreabilidade operacional em PostgreSQL e integridade histórica pertencem à FASE 4;
- nenhuma integração externa, corretora, login, ordem ou dinheiro real foi adicionada.
