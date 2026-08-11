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

### Replay cursor

O replay possui uma posição/relógio operacional corrente, conceitualmente:

```text
replay_cursor_time
```

No `ReplaySource` vigente, esse cursor pode avançar e pode ser rebobinado por `reset`. Essa semântica pertence à FASE 1 e permanece válida.

Por ser rebobinável, o cursor **não pode** ser interpretado por consumidores experimentais posteriores como prova de que instantes posteriores nunca foram expostos antes.

### Session Exposure Watermark

Para Outcome Evaluation, cada sessão/experimento deve possuir conceitualmente uma fronteira temporal de exposição separada:

```text
session_exposure_watermark
```

Semântica:

```text
maior instante lógico de mercado
já exposto na sessão/experimento
```

Antes da primeira exposição, utiliza a origem lógica determinística/timezone-aware da sessão como baseline.

Invariante:

```text
W_new >= W_old
```

Portanto:

- avanço além do máximo anterior aumenta o watermark;
- `reset` pode rebobinar `replay_cursor_time`, mas não reduz watermark;
- pause/resume não reduz watermark;
- reexecução abaixo do máximo anterior não reduz watermark;
- nova máxima exposição aumenta watermark;
- novo experimento/sessão possui watermark próprio;
- reset da mesma sessão não é nova sessão.

A fronteira pertence ao estado auditável da sessão/experimento e, quando implementada na FASE 7, deve sobreviver a reinvocação/restart conforme o contrato de persistência. Ela contém somente timestamp de exposição, nunca OHLC/features.

### `OutcomeEvaluationPolicy`
Contrato da FASE 7 para comprometer a definição do target antes do futuro avaliado poder influenciar sua escolha.

No MVP:

```text
Session 1 → 0..1 OutcomeEvaluationPolicy
```

A policy contém identidade estável, `session_id`, horizonte, threshold e `bound_at`.

`bound_at` é capturado do **session exposure watermark não rebobinável** no momento do registro da policy. Ele não pode ser backdated arbitrariamente pelo chamador e não pode derivar exclusivamente do cursor corrente do replay.

Uma Analysis da sessão somente é elegível quando:

```text
policy.bound_at <= Analysis.timestamp
```

A comparação é inclusiva: igualdade pode ser elegível; `Analysis.timestamp < policy.bound_at` é rejeitado.

A policy é imutável. Alterar horizonte/threshold exige nova sessão/experimento no MVP; múltiplas policies por sessão são `FUTURE`. `reset` operacional da mesma sessão não permite criar outro target.

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
Replay / sessão
   │
   ├── replay cursor — rewindable
   │        │
   │        └── reset pode rebobinar
   │
   └── session exposure watermark — monotonic
              │
              │ reset NÃO reduz
              ▼
OutcomeEvaluationPolicy
   │  configuração imutável
   │  bound_at = watermark no registro
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
reset
   ↓
cursor rebobinado
   X→ backdate de OutcomeEvaluationPolicy.bound_at
```

```text
Outcome
   X→ UPDATE Analysis
```

Ground Truth posterior pode permitir Outcome, mas nunca alterar `Analysis(T)` nem a policy previamente comprometida.

O exposure watermark não é Ground Truth de mercado: ele registra somente a maior fronteira temporal já exposta e não pode alimentar features ou classificação.

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
   │
   ├── session_origin_time
   ├── session_exposure_watermark (monotonic)
   │
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

A representação física futura pode manter o watermark em `sessions` ou registro equivalente, mas deve preservar a semântica: estado por sessão, baseline determinístico, monotonicidade, durabilidade e impossibilidade de redução por reset.

No MVP da FASE 7:

- `outcome_evaluation_policies` é conceitualmente imutável e possui no máximo uma linha por sessão;
- `OutcomeEvaluationPolicy.bound_at` captura a fronteira de exposição persistida da sessão;
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
12. replay cursor rebobinável não é prova suficiente de precommit;
13. session exposure watermark é monotonicamente não decrescente e reset não o reduz;
14. `policy.bound_at` usa a fronteira não rebobinável, não o cursor rebobinado;
15. policy tardia não pode tornar Analysis histórica retroativamente elegível;
16. reset da mesma sessão não cria novo experimento nem permite outro target;
17. métricas não misturam `policy_id` diferentes no mesmo cohort;
18. confidence calibration obedece à mesma fronteira de cohort;
19. exposure watermark não fornece OHLC/features ao módulo de Analysis ou visão;
20. uma fase não antecipa componentes da fase seguinte sem necessidade estrutural explícita;
21. simplicidade prevalece sobre abstração prematura.

## Stack congelada do v1

- Backend: Python + FastAPI
- Frontend: React + TypeScript + Vite
- Banco: PostgreSQL
- Visão: OpenCV
- Orquestração local/CI: Docker Compose
- Gráfico controlado: TradingView Lightweight Charts ou substituto compatível aprovado sem violar os contratos

Não adicionar Redis, banco vetorial ou TimescaleDB no v1 sem decisão registrada.
