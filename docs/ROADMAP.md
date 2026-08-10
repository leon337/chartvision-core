# ChartVision Core — Roadmap Oficial

> Status: **FROZEN v1**
>
> Este documento é a fonte de verdade para a sequência de desenvolvimento. Nenhuma fase pode ser pulada, ampliada ou reordenada sem decisão explícita registrada em `docs/DECISIONS.md` e atualização de `docs/SCOPE.md`.

## Estado global

| Fase | Nome | Estado |
|---|---|---|
| 0 | Foundation | ✅ PASS |
| 1 | Replay MVP | ✅ PASS |
| 2 | Visual Observer MVP | ✅ PASS |
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

## FASE 2 — VISUAL OBSERVER MVP — ✅ PASS

### Objetivo
Observar o gráfico renderizado estritamente como imagem.

### Entregas concluídas
- `CaptureService` com captura/crop da região controlada, hash de pixels, detecção de mudança e intervalo padrão de 5 segundos;
- `ChartDetector` para área útil do gráfico, região de candles e localização visual da escala de preço;
- `CandleDetector` visual inicial para X, corpo, pavios, largura, direção e confiança;
- contratos de geometria, confiança, qualidade e falhas explícitas;
- `OpenCVVisionProvider` com entrada somente `image: bytes`;
- cenário visual controlado de referência e testes de fronteira arquitetural.

### Evidência de fechamento
- branch `phase-2-visual-observer-mvp`;
- PR `#3 — feat: complete Phase 2 Visual Observer MVP` — merged;
- HEAD técnico `83d5b8dc7c94fdc472a3049bb30f835454e45d1a`;
- merge em `main` `afc028a6c966ec8be628dee59b9aa432ebd8921c`;
- CI técnico run `#34` / `31407809004` — SUCCESS;
- CI de PR run `#35` / `31408022011` — SUCCESS;
- CI pós-merge run `#36` / `31408244075` — SUCCESS;
- `ruff check app` — PASS;
- `pytest -q` — 19 testes aprovados;
- `npm run build` — PASS;
- stack Docker completa — PASS.

### Critérios de aceite verificados
- módulo visual recebe imagem/pixels e não acessa OHLC do `ReplaySource` nem Ground Truth;
- cenário visual controlado identifica os 3 candles visíveis de referência com geometria, direção e confiança;
- gráfico ausente, imagem de baixa qualidade, escala não localizada e ausência de candles geram estados explícitos sem dados inventados;
- captura gera hash e mudança/não mudança de frame, mantendo 5 segundos como intervalo padrão;
- não existe conversão pixel → preço, tracking, normalização ou reconstrução OHLC nesta fase.

### Limitações preservadas
- detector inicial calibrado para tema/tamanho/cores controlados do v1;
- persistência temporal continua reservada à FASE 4;
- `PriceMapper`, `ChartTracker`, `Normalizer` e reconstrução OHLC permanecem para a FASE 3.

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

### Autorização
É a próxima fase autorizável após o PASS formal da FASE 2, exclusivamente em novo chat dedicado e após novo `chartvision-phase-start` resultar em READY.

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
