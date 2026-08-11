# Evaluation Metrics — Percepção e FASE 7

## Objetivo

Definir métricas auditáveis tanto para a qualidade da percepção/reconstrução quanto para a avaliação das classificações da FASE 7.

## Qualidade da percepção — FASE 3 ✅ PASS

A FASE 3 implementa um `ReconstructionEvaluator` separado do pipeline visual. Ground Truth só é fornecido a esse avaliador **depois** de os candles terem sido reconstruídos.

Métricas implementadas:
- Open error;
- High error;
- Low error;
- Close error;
- candle detection rate;
- direction accuracy;
- duplicate rate;
- missing candle rate.

### Evidência do cenário controlado
Na integração de três frames da FASE 3:
- Open error = `0`;
- High error = `0`;
- Low error = `0`;
- Close error = `0`;
- candle detection rate = `1.0`;
- direction accuracy = `1.0`;
- duplicate rate = `0.0`;
- missing candle rate = `0.0`.

Esses resultados validam o cenário de referência controlado. Não representam threshold universal nem generalização para fontes externas.

### Regra de isolamento
Ground Truth não pode ser importado ou fornecido a `ChartDetector`, `CandleDetector`, `OpenCVPriceScaleReader`, `PriceMapper`, `ChartTracker`, `Normalizer` ou `CandleReconstructionPipeline`.

O teste arquitetural da FASE 3 verifica essa fronteira.

## FASE 7 — Outcome Evaluation — ⬜ PENDING / CONTRATO DEFINIDO

A especificação funcional canônica da FASE 7 está em:

```text
docs/outcome_evaluation.md
```

Esse documento é a autoridade para:

- definição de `Outcome`, `OutcomeConfig` e `OutcomeEvaluationPolicy`;
- precommit temporal da configuração;
- separação entre replay cursor rebobinável e session exposure watermark monotônico;
- identidade e imutabilidade da policy;
- horizonte temporal;
- Ground Truth boundary;
- `RealizedState`;
- política de `UNCERTAIN`;
- fórmulas de accuracy, precision, recall, confusion matrix e coverage;
- uncertain count/frequency;
- confidence calibration diagnóstica;
- persistência, identidade e idempotência;
- cohort métrico homogêneo;
- critérios de aceite e test plan.

### Princípio de imutabilidade

Uma `Analysis` registrada não pode ser alterada após conhecer o futuro.

A definição do target também não pode ser escolhida retroativamente. Horizonte e threshold devem estar comprometidos em uma `OutcomeEvaluationPolicy` imutável sob uma fronteira temporal não rebobinável, conforme `docs/outcome_evaluation.md`.

O futuro somente pode ser associado posteriormente pelo Outcome Evaluation, preservando:
- classificação original;
- confidence original;
- evidências originais;
- qualidade de dados original;
- timestamp original;
- policy/configuração previamente comprometida.

### Precommit resistente a reset

O cursor operacional do replay pode ser rebobinado por `reset`, portanto não constitui prova suficiente de que o futuro nunca foi visto.

A FASE 7 usa conceitualmente:

```text
session_exposure_watermark
```

como a maior fronteira lógica já exposta na sessão. Essa fronteira é monotonicamente não decrescente e não é reduzida por reset, pause/resume ou reexecução abaixo do máximo anterior.

A policy captura:

```text
policy.bound_at = session_exposure_watermark
```

no instante do registro. Assim, observar futuro até `W`, resetar o replay e registrar policy não torna uma Analysis com `T < W` elegível.

O exposure watermark contém somente metadado temporal de auditoria. Ele não fornece OHLC, features ou realized state ao módulo de Analysis.

### Classes

Predição/Analysis:

```text
UP
DOWN
SIDEWAYS
UNCERTAIN
```

Resultado realizado:

```text
UP
DOWN
SIDEWAYS
```

`UNCERTAIN` é abstention da previsão e nunca é resultado realizado.

### Métricas normativas

A FASE 7 deve produzir:
- accuracy;
- precision por `UP`, `DOWN` e `SIDEWAYS`;
- recall por `UP`, `DOWN` e `SIDEWAYS`;
- matriz de confusão com linhas realizadas e colunas previstas, incluindo coluna `UNCERTAIN`;
- coverage;
- `uncertain_count`;
- `uncertain_frequency`;
- relatório de confidence calibration operacional por bins e weighted alignment gap.

As fórmulas, denominadores, ordem das classes e comportamento de denominador zero estão definidos exclusivamente em `docs/outcome_evaluation.md` para evitar duplicação normativa divergente.

## Cohort métrico obrigatório

Toda métrica agregada da FASE 7 é válida somente dentro de um target homogêneo.

Contrato canônico:

```text
Metrics Cohort = exatamente um OutcomeEvaluationPolicy.policy_id
```

Portanto, confusion matrix, accuracy, precision, recall, coverage, uncertain frequency e confidence calibration não podem combinar Outcomes de policies diferentes.

Cada relatório deve identificar a policy/configuração do cohort, incluindo pelo menos:

```text
policy_id
horizon_closed_candles
realized_return_threshold
```

Entrada contendo Outcomes de policies diferentes deve falhar explicitamente antes de qualquer agregação, ou ser previamente separada em relatórios independentes. O MVP canônico escolhe falha explícita para uma entrada mista; não existe soma silenciosa de cohorts heterogêneos.

Confidence calibration obedece à mesma fronteira: os cinco bins e o `weighted_alignment_gap` são calculados dentro de um único `policy_id`.

A correção de exposure watermark não altera esse contrato. `BLOCKER-14` permanece resolvido.

## Regra contra future leakage e hindsight bias

Nenhum dado posterior ao timestamp de uma Analysis pode ser usado para produzir aquela Analysis.

A informação posterior somente entra na camada de Outcome Evaluation após o registro imutável da Analysis e respeitando o corte `evaluation_as_of` e o horizonte comprometido pela policy.

Também é proibido observar o futuro e depois escolher retroativamente `horizon_closed_candles` ou `realized_return_threshold` para modificar o significado do Outcome de uma Analysis histórica.

`reset` do replay não reabre essa possibilidade: o cursor pode voltar, mas a fronteira de exposição experimental não diminui.

## Interpretação

O objetivo do v1 é medir:
1. qualidade da percepção;
2. integridade da memória temporal;
3. consistência da classificação;
4. capacidade de verificar resultados sob target experimental previamente comprometido e temporalmente auditável.

Rentabilidade financeira não é critério de sucesso do v1.
