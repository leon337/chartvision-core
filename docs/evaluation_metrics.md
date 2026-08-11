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

- definição de `Outcome` e `OutcomeConfig`;
- horizonte temporal;
- Ground Truth boundary;
- `RealizedState`;
- política de `UNCERTAIN`;
- fórmulas de accuracy, precision, recall, confusion matrix e coverage;
- uncertain count/frequency;
- confidence calibration diagnóstica;
- persistência, identidade e idempotência;
- critérios de aceite e test plan.

### Princípio de imutabilidade

Uma `Analysis` registrada não pode ser alterada após conhecer o futuro.

O futuro somente pode ser associado posteriormente pelo Outcome Evaluation, preservando:
- classificação original;
- confidence original;
- evidências originais;
- qualidade de dados original;
- timestamp original.

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

## Regra contra future leakage

Nenhum dado posterior ao timestamp de uma Analysis pode ser usado para produzir aquela Analysis.

A informação posterior somente entra na camada de Outcome Evaluation após o registro imutável da Analysis e respeitando o corte `evaluation_as_of` e o horizonte descritos em `docs/outcome_evaluation.md`.

## Interpretação

O objetivo do v1 é medir:
1. qualidade da percepção;
2. integridade da memória temporal;
3. consistência da classificação;
4. capacidade de verificar resultados.

Rentabilidade financeira não é critério de sucesso do v1.
