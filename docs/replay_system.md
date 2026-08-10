# Replay System — FASE 1

## Objetivo

Reproduzir dados OHLC históricos de forma determinística como se estivessem ocorrendo no tempo, alimentando um gráfico controlado.

## Responsabilidades do `ReplaySource`

- carregar dataset de referência;
- iniciar;
- pausar;
- continuar;
- reiniciar;
- avançar o relógio do replay;
- liberar somente dados disponíveis até o instante atual;
- produzir sempre a mesma sequência para o mesmo dataset/configuração.

## Responsabilidades do `ChartRenderer`

- consumir estado permitido pelo replay;
- renderizar candles;
- manter apresentação visual controlada;
- não conter lógica de análise;
- não entregar Ground Truth ao pipeline visual futuro.

## Separação obrigatória

```text
Dataset
   ↓
ReplaySource
   ├────────► Ground Truth
   ↓
ChartRenderer
   ↓
Imagem
```

## Controles do MVP

- Start
- Pause
- Resume
- Reset

## Regras

1. um único ativo por sessão;
2. timeframe inicial de 1 minuto;
3. replay determinístico;
4. sem OpenCV nesta fase;
5. sem OCR nesta fase;
6. sem AnalysisEngine;
7. sem OutcomeEvaluator;
8. sem integrações externas;
9. nenhum dado futuro deve aparecer antes da hora.

## Critérios de aceite

- duas execuções equivalentes produzem a mesma sequência;
- pause congela corretamente a progressão;
- resume continua do mesmo ponto;
- reset volta ao estado inicial;
- testes automatizados cobrem determinismo e controles;
- CI passa;
- documentação e `PROJECT_STATE.md` são atualizados antes do PASS.