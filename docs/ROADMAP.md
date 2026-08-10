# ChartVision Core — Roadmap Oficial

> Status: **FROZEN v1**
>
> Este documento é a fonte de verdade para a sequência de desenvolvimento. Nenhuma fase pode ser pulada, ampliada ou reordenada sem uma decisão explícita registrada em `docs/DECISIONS.md` e atualização de `docs/SCOPE.md`.

## Estado global

| Fase | Nome | Estado |
|---|---|---|
| 0 | Foundation | ✅ PASS |
| 1 | Replay MVP | ⬜ PENDING |
| 2 | Visual Observer MVP | ⬜ PENDING |
| 3 | Candle Reconstruction MVP | ⬜ PENDING |
| 4 | Temporal Memory MVP | ⬜ PENDING |
| 5 | Market Features MVP | ⬜ PENDING |
| 6 | Analysis Lab MVP | ⬜ PENDING |
| 7 | Outcome Evaluation MVP | ⬜ PENDING |
| 8 | Dashboard MVP | ⬜ PENDING |

## Regra de progressão

Uma fase somente muda para `PASS` quando:

1. a implementação do escopo da fase está completa;
2. testes definidos para a fase passam;
3. CI passa;
4. critérios de aceite foram verificados com evidência;
5. `docs/PROJECT_STATE.md` foi atualizado;
6. a fase seguinte continua bloqueada até o PASS.

Executar código não significa concluir uma fase.

---

## FASE 0 — FOUNDATION — ✅ PASS

### Objetivo
Estabelecer a base executável e testável do projeto.

### Entregas
- monorepo;
- backend FastAPI;
- frontend React + TypeScript + Vite;
- PostgreSQL;
- Docker Compose;
- configuração por ambiente;
- logging estruturado;
- testes iniciais;
- lint;
- CI;
- health checks;
- contratos arquiteturais iniciais.

### Evidência atual
O CI valida backend, frontend e a stack Docker completa, incluindo o endpoint `/health`.

---

## FASE 1 — REPLAY MVP — ⬜ PENDING

### Objetivo
Reproduzir um dataset OHLC de forma determinística em um gráfico controlado.

### Entregas
- `ReplaySource`;
- dataset de referência;
- `ChartRenderer`;
- iniciar;
- pausar;
- continuar;
- reiniciar;
- relógio de replay determinístico.

### Critérios de aceite
- o mesmo dataset gera exatamente a mesma sequência em execuções repetidas;
- controles de replay funcionam;
- nenhum componente de visão é implementado nesta fase;
- nenhum dado de candle futuro é exposto ao consumidor antes do instante correto.

---

## FASE 2 — VISUAL OBSERVER MVP — ⬜ PENDING

### Objetivo
Observar o gráfico renderizado estritamente como imagem.

### Entregas
- `CaptureService`;
- captura da região do gráfico;
- `ChartDetector`;
- `CandleDetector` visual inicial;
- detecção de mudança de frame;
- confiança visual.

### Critérios de aceite
- módulo visual não pode acessar OHLC do `ReplaySource`;
- candles visíveis devem ser identificados no cenário de referência;
- falhas de leitura devem gerar estado explícito, nunca dados inventados.

---

## FASE 3 — CANDLE RECONSTRUCTION MVP — ⬜ PENDING

### Objetivo
Converter elementos visuais em candles normalizados e compará-los ao Ground Truth.

### Entregas
- `PriceMapper`;
- `ChartTracker`;
- `Normalizer`;
- reconstrução OHLC;
- identificação de candle aberto/fechado;
- deduplicação temporal.

### Métricas obrigatórias
- erro de Open;
- erro de High;
- erro de Low;
- erro de Close;
- taxa de detecção;
- acurácia de direção;
- taxa de duplicação;
- taxa de candles ausentes.

### Gate
Não avançar se a reconstrução não estiver estável no dataset de referência.

---

## FASE 4 — TEMPORAL MEMORY MVP — ⬜ PENDING

### Objetivo
Persistir a evolução temporal do gráfico com integridade e rastreabilidade.

### Entregas
- sessions;
- frames;
- observations;
- candles;
- timestamps;
- deduplicação;
- fechamento de candle;
- rastreabilidade entre frame e dado reconstruído.

### Critérios de aceite
- replays repetidos não corrompem dados;
- candles não são duplicados dentro da mesma sessão;
- dados históricos não são sobrescritos silenciosamente.

---

## FASE 5 — MARKET FEATURES MVP — ⬜ PENDING

### Objetivo
Gerar características estruturadas a partir dos candles normalizados.

### Implementar somente
- direção;
- amplitude;
- retorno;
- volatilidade simples;
- HH;
- HL;
- LH;
- LL;
- tendência básica;
- lateralização básica.

### Critérios de aceite
Todos os cálculos devem possuir testes unitários determinísticos.

---

## FASE 6 — ANALYSIS LAB MVP — ⬜ PENDING

### Objetivo
Classificar o estado do gráfico em ambiente de replay, usando apenas informação disponível até o instante analisado.

### Estados de saída
- `UP`;
- `DOWN`;
- `SIDEWAYS`;
- `UNCERTAIN`.

### Metadados
- confiança;
- evidências;
- qualidade dos dados.

### Regra crítica
É proibido qualquer `future leakage`.

### Critério de aceite
Teste automatizado comprova que nenhum candle futuro participa da análise.

---

## FASE 7 — OUTCOME EVALUATION MVP — ⬜ PENDING

### Objetivo
Comparar análises registradas com o que ocorreu posteriormente no replay.

### Métricas
- accuracy;
- precision por classe;
- recall por classe;
- matriz de confusão;
- cobertura;
- quantidade de `UNCERTAIN`;
- calibração de confiança.

### Regra
A previsão original nunca pode ser alterada retrospectivamente.

---

## FASE 8 — DASHBOARD MVP — ⬜ PENDING

### Objetivo
Disponibilizar uma interface única para observação e auditoria do laboratório.

### Tela única
Deve apresentar:
- gráfico;
- estado do replay;
- qualidade visual;
- estado estrutural;
- confiança;
- observações;
- métricas.

### Fora desta fase
Não criar páginas extras, multiusuário, notificações ou integrações externas.

---

# Definition of Done do v1

O v1 somente estará concluído quando for possível executar e auditar de ponta a ponta:

```text
DATASET
  ↓
REPLAY
  ↓
GRÁFICO VISUAL
  ↓
CAPTURA
  ↓
VISÃO COMPUTACIONAL
  ↓
CANDLES RECONSTRUÍDOS
  ↓
MEMÓRIA TEMPORAL
  ↓
FEATURES
  ↓
ANÁLISE EXPERIMENTAL
  ↓
RESULTADO FUTURO
  ↓
AVALIAÇÃO
  ↓
DASHBOARD
```

## Critérios finais de sucesso

1. **Percepção** — o sistema observa corretamente o gráfico.
2. **Memória** — constrói histórico confiável.
3. **Interpretação** — transforma histórico em estado estruturado.
4. **Verificação** — compara suas classificações com o que ocorreu depois.

O sucesso do v1 não é definido por rentabilidade financeira.

---

# Pós-v1 — somente após autorização explícita

A arquitetura deve permitir futuros `ChartSource`/adapters, mas nenhuma integração externa faz parte do v1. Qualquer evolução pós-v1 exige novo escopo e decisão registrada.