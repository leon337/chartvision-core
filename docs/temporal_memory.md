# ChartVision Core — Temporal Memory MVP

## Escopo da FASE 4

A FASE 4 persiste a evolução temporal produzida pelas fases anteriores sem introduzir cálculo de `MarketFeatures`.

Entidades persistidas:
- `Session`;
- `Frame`;
- `Observation`;
- `Candle` reconstruído;
- snapshots imutáveis de candle por observação para rastreabilidade histórica.

## Fluxo persistente

```text
sessions
  ↓
frames
  ↓
observations
  ↓
candle_snapshots ──► candles
```

`candles` mantém o estado canônico mais recente de cada identidade de candle dentro da sessão. `candle_snapshots` mantém o estado reconstruído observado em cada instante e nunca é sobrescrito.

## Identidades

### Session

Identidade: `session_id`.

Persistir novamente o mesmo payload é idempotente. O mesmo `session_id` com payload diferente produz conflito explícito.

### Frame

Identidade: `frame_id`.

Frames distintos podem possuir o mesmo `image_hash`, pois capturas diferentes podem representar os mesmos pixels. Hash de imagem não é usado como identidade temporal.

### Observation

Identidade: `observation_id`.

Cada observação referencia `session_id` e `frame_id`. O banco impõe que o frame e a observação pertençam à mesma sessão.

### Candle

Identidade persistente do v1: `(session_id, open_time)`.

O escopo congelado define um único ativo e timeframe por sessão, portanto essa chave identifica um candle sem introduzir um identificador artificial no modelo canônico.

## Evolução e deduplicação de candles

- um candle aberto pode receber estados posteriores sem criar nova linha canônica;
- `open`, identidade, contexto, `open_time` e `close_time` são imutáveis;
- `high` não pode diminuir em uma atualização temporal posterior;
- `low` não pode aumentar em uma atualização temporal posterior;
- um candle pode transitar de aberto para fechado;
- um candle fechado não pode ser reaberto nem reescrito;
- estados históricos repetidos de um replay podem ser persistidos como novos snapshots sem regredir o estado canônico;
- dois resultados diferentes para o mesmo candle no mesmo timestamp lógico geram conflito explícito.

Esse contrato fornece deduplicação persistente sem confundir replay histórico com atualização temporal futura.

## Rastreabilidade frame → reconstrução

Cada `Observation` referencia um `Frame`. Cada estado de candle persistido por uma observação gera um registro imutável em `candle_snapshots`.

Assim, a consulta de candles por `frame_id` retorna o estado reconstruído daquele frame, mesmo depois que o candle canônico foi atualizado ou fechado.

Essa separação evita que uma atualização posterior apague silenciosamente o que havia sido reconstruído em um frame anterior.

## Timestamps

Timestamps persistidos são timezone-aware e normalizados para UTC no repositório:
- `Session.started_at` / `ended_at`;
- `Frame.captured_at`;
- `Observation.timestamp`;
- `Candle.open_time` / `close_time`.

Timestamps naive são recusados explicitamente.

## Integridade PostgreSQL

O schema usa:
- primary keys/unique constraints para identidade e deduplicação;
- foreign keys com `RESTRICT` para preservar rastreabilidade;
- checks de strings obrigatórias;
- dimensões positivas para frames;
- confiança/qualidade no intervalo `[0, 1]`;
- coerência temporal de candles;
- coerência OHLC básica.

Alembic é o mecanismo oficial de schema. Não é usado `Base.metadata.create_all()`.

## Critérios de aceite da FASE 4

1. **Replays repetidos não corrompem dados** — o mesmo histórico lógico pode ser reapresentado com novos frames/observações sem regredir o candle canônico; snapshots históricos permanecem auditáveis.
2. **Candles não são duplicados dentro da mesma sessão** — a identidade `(session_id, open_time)` é chave primária de `candles`.
3. **Dados históricos não são sobrescritos silenciosamente** — snapshots por observação são imutáveis; divergências no mesmo timestamp, regressões temporais e alterações após fechamento falham explicitamente.

## Limites preservados

A FASE 4 não implementa:
- direção/amplitude/retorno/volatilidade/estrutura HH-HL-LH-LL;
- tendência ou lateralização;
- `FeatureEngine` funcional;
- análise de mercado;
- avaliação de outcomes;
- dashboard;
- integrações externas ou execução financeira.

Esses itens pertencem às fases posteriores do roadmap.
