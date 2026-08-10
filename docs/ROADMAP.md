# ChartVision Core — Roadmap Oficial

> Status: **FROZEN v1**
>
> Este documento é a fonte de verdade para a sequência de desenvolvimento. Nenhuma fase pode ser pulada, ampliada ou reordenada sem decisão explícita registrada em `docs/DECISIONS.md` e atualização de `docs/SCOPE.md`.

## Estado global

| Fase | Nome | Estado |
|---|---|---|
| 0 | Foundation | ✅ PASS |
| 1 | Replay MVP | ✅ PASS |
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
5. ausência de regressão/scope creep relevante foi verificada;
6. `docs/PROJECT_STATE.md` foi atualizado;
7. este roadmap e a Issue Mestra #1 foram atualizados;
8. o procedimento `chartvision-phase-close` resultou em PASS ou foi reproduzido integralmente.

Executar código não significa concluir uma fase.

## Lifecycle de cada fase

Antes de implementar:

```text
chartvision-phase-start
→ recuperar estado real
→ confirmar fase autorizada
→ produzir Phase Brief
```

Depois da implementação e testes:

```text
chartvision-phase-close
→ validar Definition of Done
→ persistir memória
→ PASS / FAIL / BLOCKED
```

O PASS de uma fase apenas autoriza abrir o chat da próxima fase. Não inicia automaticamente sua implementação.

---

## FASE 0 — FOUNDATION — ✅ PASS

### Objetivo
Estabelecer a base executável, testável e governável do projeto.

### Evidência
Foundation validada com FastAPI, React + TypeScript + Vite, PostgreSQL, Docker Compose, health check, testes, lint, build frontend, CI e governança persistente.

---

## FASE 1 — REPLAY MVP — ✅ PASS

### Objetivo
Reproduzir um dataset OHLC de forma determinística em um gráfico controlado.

### Entregas concluídas
- `ReplaySource`;
- dataset de referência;
- `ChartRenderer`;
- Start;
- Pause;
- Resume;
- Reset;
- relógio virtual determinístico;
- gate temporal para impedir exposição antecipada de candles.

### Evidência de fechamento
- PR `#2 — feat: complete Phase 1 Replay MVP`;
- HEAD técnico: `f335a35bbd028e4e8050d995fea8b4c5a907a0a5`;
- merge em `main`: `821bce313295701fd69cd1925fa9f4a3726cb731`;
- CI técnico run `#28` — SUCCESS;
- CI de PR run `#29` — SUCCESS;
- CI pós-merge run `#30` — SUCCESS;
- `ruff check app` — PASS;
- `pytest -q` — 8 testes aprovados;
- `npm run build` — PASS;
- stack Docker completa — PASS.

### Critérios de aceite verificados
- mesmo dataset/configuração gera exatamente a mesma sequência em execuções repetidas;
- Pause congela progressão;
- Resume continua do mesmo ponto;
- Reset volta ao estado inicial;
- nenhum componente de visão foi implementado;
- candle futuro não é exposto antes do `close_time`.

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

### Autorização
É a próxima fase autorizável, exclusivamente em novo chat dedicado e somente após novo `chartvision-phase-start` resultar em READY.

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
- erro de Open, High, Low e Close;
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
- HH, HL, LH, LL;
- tendência básica;
- lateralização básica.

### Critério de aceite
Todos os cálculos devem possuir testes unitários determinísticos.

---

## FASE 6 — ANALYSIS LAB MVP — ⬜ PENDING

### Objetivo
Classificar o estado do gráfico usando somente informação disponível até o instante analisado.

### Estados
- `UP`;
- `DOWN`;
- `SIDEWAYS`;
- `UNCERTAIN`.

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
Deve apresentar gráfico, estado do replay, qualidade visual, estado estrutural, confiança, observações e métricas.

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

O sucesso do v1 não é definido por rentabilidade financeira.

# Pós-v1

A arquitetura deve permitir futuros `ChartSource`/adapters, mas nenhuma integração externa faz parte do v1. Qualquer evolução pós-v1 exige novo escopo e decisão registrada.
