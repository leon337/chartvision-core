# Evaluation Metrics — Percepção e FASE 7

## Objetivo

Definir métricas auditáveis tanto para a qualidade da percepção/reconstrução quanto, futuramente, para a avaliação das classificações da FASE 7.

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

## FASE 7 — Outcome Evaluation — ⬜ PENDING

### Objetivo
Avaliar, de forma auditável, classificações registradas pelo sistema contra resultados observados posteriormente no replay.

### Princípio de imutabilidade
Uma `Analysis` registrada não pode ser alterada após conhecer o futuro.

O futuro somente pode ser associado posteriormente pelo `OutcomeEvaluator`, preservando:
- classificação original;
- confiança original;
- evidências originais;
- qualidade de dados original;
- timestamp original.

### Classes previstas
- `UP`;
- `DOWN`;
- `SIDEWAYS`;
- `UNCERTAIN`.

### Métricas previstas
- accuracy;
- precision por classe;
- recall por classe;
- matriz de confusão;
- cobertura;
- frequência de `UNCERTAIN`;
- calibração de confiança.

## Regra contra future leakage

Nenhum dado posterior ao timestamp de uma análise pode ser usado para produzir aquela análise.

A informação futura somente entra no `OutcomeEvaluator`, após o horizonte de avaliação.

## Interpretação

O objetivo do v1 é medir:
1. qualidade da percepção;
2. integridade da memória temporal;
3. consistência da classificação;
4. capacidade de verificar resultados.

Rentabilidade financeira não é critério de sucesso do v1.
