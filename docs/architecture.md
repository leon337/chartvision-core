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

### `OutcomeEvaluationPolicy`
Contrato da FASE 7 para comprometer a definição do target antes do futuro avaliado poder influenciar sua escolha.

No MVP:

```text
Session 1 → 0..1 OutcomeEvaluationPolicy
```

A policy contém identidade estável, `session_id`, horizonte, threshold e `bound_at`.

`bound_at` é capturado do relógio lógico autoritativo da sessão no momento do registro da policy e não pode ser backdated arbitrariamente pelo chamador.

Uma Analysis da sessão somente é elegível quando:

```text
policy.bound_at <= Analysis.timestamp
```

A policy é imutável. Alterar horizonte/threshold exige nova sessão/experimento no MVP; múltiplas policies por sessão são `FUTURE`.

O contrato detalhado fica em `docs/outcome_evaluation.md`.

### `GroundTruthProvider`
Contrato exclusivo da camada de avaliação posterior.

Na FASE 7, deve fornecer somente a janela Ground Truth necessária para avaliar uma `Analysis` já persistida, respeitando `Analysis.timestamp`, `evaluation_as_of` e o horizonte previamente comprometido na `OutcomeEvaluationPolicy`.

Ele pode ser implementado por um adapter do replay controlado, mas:

- não pode ser consumido por `AnalysisEngine`;
- não pode ser consumido por `AnalysisLabService`;
- não pode ser consumido pelo pipeline visual;
- não transforma Ground Truth em entrada da análise histórica;
- não pode ser usado para escolher retrospectivamente horizonte ou threshold.

O contrato detalhado fica em `docs/outcome_evaluation.md`.

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
   │                       │
   │                       └────────► GroundTruthProvider
   │                                      │
   │                                      ▼
   │                              Outcome Evaluation
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

A fronteira temporal adicional da FASE 7 é:

```text
Session / experimento
   │
   ▼
OutcomeEvaluationPolicy
   │  configuração imutável
   │  bound_at do relógio lógico da sessão
   │
   └──────────────► policy.bound_at <= Analysis.timestamp
                              │
                              ▼
                         Analysis(T)
                              │
                              │ imutável
                              ▼
                    OutcomeEvaluationService
                              │
                              ├── Analysis + Policy persistidas
                              └── GroundTruthProvider
                                        │
                                        ▼
                                OutcomeEvaluator
                                        │
                                        ▼
                                     Outcome
                                        │
                                        ▼
                              Metrics por policy_id
```

Fluxos obrigatoriamente proibidos:

```text
Ground Truth
   X→ AnalysisEngine
```

```text
Ground Truth conhecido
   X→ nova configuração retroativa para Analysis(T)
```

```text
Outcome
   X→ UPDATE Analysis
```

Ground Truth posterior pode permitir Outcome, mas nunca alterar `Analysis(T)` nem a policy previamente comprometida.

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
   ├────────────► outcome_evaluation_policies
   │                       │
   ▼                       │
frames                     │
   ↓                       │
observations               │
   ↓                       │
candles                    │
   ↓                       │
features                   │
   ↓                       │
analyses ◄─────────────────┘
   ↓
outcomes
```

No MVP da FASE 7:

- `outcome_evaluation_policies` é conceitualmente imutável e possui no máximo uma linha por sessão;
- `outcomes` referencia `Analysis` e a policy usada;
- o Outcome copia horizonte/threshold para auditoria, mas deve corresponder exatamente à policy;
- métricas agregadas são derivadas de `Analysis + Outcome` dentro de um único `policy_id`;
- não é necessária tabela persistente de métricas sem nova decisão.

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
9. Ground Truth posterior entra somente pela camada de avaliação autorizada;
10. OutcomeEvaluator permanece desacoplado de ReplaySource e infraestrutura;
11. definição de Outcome deve estar pré-comprometida por policy antes da Analysis elegível;
12. policy tardia não pode tornar Analysis histórica retroativamente elegível;
13. métricas não misturam `policy_id` diferentes no mesmo cohort;
14. confidence calibration obedece à mesma fronteira de cohort;
15. uma fase não antecipa componentes da fase seguinte sem necessidade estrutural explícita;
16. simplicidade prevalece sobre abstração prematura.

## Stack congelada do v1

- Backend: Python + FastAPI
- Frontend: React + TypeScript + Vite
- Banco: PostgreSQL
- Visão: OpenCV
- Orquestração local/CI: Docker Compose
- Gráfico controlado: TradingView Lightweight Charts ou substituto compatível aprovado sem violar os contratos

Não adicionar Redis, banco vetorial ou TimescaleDB no v1 sem decisão registrada.
