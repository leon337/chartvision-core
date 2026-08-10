# Evaluation Metrics — FASE 7

## Objetivo

Avaliar, de forma auditável, classificações registradas pelo sistema contra resultados observados posteriormente no replay.

## Princípio de imutabilidade

Uma `Analysis` registrada não pode ser alterada após conhecer o futuro.

O `OutcomeEvaluator` cria um resultado associado, preservando:
- classificação original;
- confiança original;
- evidências originais;
- qualidade de dados original;
- timestamp original.

## Classes previstas

- `UP`
- `DOWN`
- `SIDEWAYS`
- `UNCERTAIN`

## Métricas obrigatórias

- accuracy;
- precision por classe;
- recall por classe;
- matriz de confusão;
- cobertura;
- frequência de `UNCERTAIN`;
- calibração de confiança.

## Qualidade da percepção

Antes da análise de classificação, as fases visuais devem medir:
- erro de Open;
- erro de High;
- erro de Low;
- erro de Close;
- taxa de detecção de candle;
- acurácia de direção visual;
- taxa de duplicação;
- taxa de candles ausentes.

## Regra contra future leakage

Nenhum dado posterior ao timestamp da análise pode ser usado para produzir aquela análise.

A informação futura somente entra no `OutcomeEvaluator`, após o horizonte de avaliação.

## Interpretação

O objetivo do v1 é medir:

1. qualidade da percepção;
2. integridade da memória temporal;
3. consistência da classificação;
4. capacidade de verificar resultados.

Rentabilidade financeira não é critério de sucesso do v1.