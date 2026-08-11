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
| 3 | Candle Reconstruction MVP | ✅ PASS |
| 4 | Temporal Memory MVP | ✅ PASS |
| 5 | Market Features MVP | 🟡 IN PROGRESS |
| 6 | Analysis Lab MVP | 🔒 BLOCKED |
| 7 | Outcome Evaluation MVP | 🔒 BLOCKED |
| 8 | Dashboard MVP | 🔒 BLOCKED |

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
- Start/Pause/Resume/Reset;
- relógio virtual determinístico;
- gate temporal contra exposição antecipada de candles.

### Evidência de fechamento
- PR `#2` — merged;
- HEAD técnico `f335a35bbd028e4e8050d995fea8b4c5a907a0a5`;
- merge `821bce313295701fd69cd1925fa9f4a3726cb731`;
- CI final run `#32` / `31374719545` — SUCCESS.

---

## FASE 2 — VISUAL OBSERVER MVP — ✅ PASS

### Objetivo
Observar o gráfico renderizado estritamente como imagem.

### Entregas concluídas
- `CaptureService`;
- `ChartDetector`;
- `CandleDetector`;
- contratos de geometria/confiança/qualidade/falhas;
- `OpenCVVisionProvider.observe(image: bytes)`;
- cenário visual controlado.

### Evidência de fechamento
- branch `phase-2-visual-observer-mvp`;
- PR `#3` — merged;
- HEAD técnico `83d5b8dc7c94fdc472a3049bb30f835454e45d1a`;
- merge `afc028a6c966ec8be628dee59b9aa432ebd8921c`;
- HEAD documental anterior `d0f28b87d4d8d9bfb8e2e706b7711d842ecad060`;
- CI final run `#37` / `31408563320` — SUCCESS.

### Critérios de aceite verificados
- visão recebe somente imagem/pixels e não acessa OHLC/Ground Truth;
- candles visíveis são identificados com geometria, direção e confiança;
- falhas retornam estados explícitos;
- `Frame` permanece separado de candle;
- pixel→preço, tracking e normalização não foram antecipados.

---

## FASE 3 — CANDLE RECONSTRUCTION MVP — ✅ PASS

### Objetivo
Converter elementos visuais em candles normalizados e compará-los ao Ground Truth somente após a reconstrução.

### Entregas concluídas
- `OpenCVPriceScaleReader` controlado para anchors derivados dos pixels da escala;
- `PriceMapper`;
- `ChartTracker`;
- `Normalizer`;
- reconstrução OHLC;
- identificação de candle aberto/fechado;
- reconhecimento de novo candle e deslocamento horizontal;
- deduplicação temporal limitada à reconstrução;
- `TRACKING_LOST` como falha explícita;
- `CandleReconstructionPipeline` sem Ground Truth;
- `ReconstructionEvaluator` pós-reconstrução.

### Métricas implementadas
- Open error;
- High error;
- Low error;
- Close error;
- candle detection rate;
- direction accuracy;
- duplicate rate;
- missing candle rate.

### Gate — PASS
O cenário controlado de três frames é estável:
- mesmo candle é atualizado em múltiplos frames sem duplicação;
- novo candle fecha o anterior;
- deslocamento horizontal de `-70 px` é reconhecido;
- três candles fechados são reconstruídos;
- Open/High/Low/Close error = `0`;
- candle detection rate = `1.0`;
- direction accuracy = `1.0`;
- duplicate rate = `0.0`;
- missing candle rate = `0.0`.

Essas métricas são evidência do dataset/fixture controlado e não um threshold universal.

### Evidência de fechamento
- branch `phase-3-candle-reconstruction-mvp`;
- HEAD técnico `b5dd7abecc8402ff825204b2bfe32cd158d2e483`;
- PR `#6 — feat: complete Phase 3 Candle Reconstruction MVP` — merged;
- merge em `main` `58f202e6ca1bfea3bf6f1f08a737a78bd3e3b71c`;
- CI técnico run `#42` / `31419351907` — SUCCESS;
- CI do PR run `#43` / `31419606685` — SUCCESS;
- CI pós-merge run `#44` / `31419758543` — SUCCESS;
- suíte específica da FASE 3 — `27 passed`;
- `ruff check app` — SUCCESS no CI;
- `pytest -q` — SUCCESS no CI;
- `npm run build` — SUCCESS no CI;
- stack Docker completa — SUCCESS no CI.

### Critérios de aceite verificados
- pixel→preço usa exclusivamente escala visual;
- OHLC é reconstruído sem OHLC verdadeiro como entrada;
- múltiplos frames podem representar o mesmo candle;
- identidade do candle é mantida entre frames;
- candle aberto é atualizado, não duplicado;
- novo candle, fechamento e deslocamento horizontal são reconhecidos;
- `Normalizer` gera o modelo canônico com confiança;
- falhas de escala/tracking são explícitas;
- teste arquitetural bloqueia dependência de replay/Ground Truth/`ChartSource` nos módulos de reconstrução;
- Ground Truth entra somente no avaliador posterior;
- as oito métricas obrigatórias estão implementadas;
- nenhuma persistência temporal funcional da FASE 4 foi antecipada.

### Limitações preservadas
- leitura de escala é calibrada ao renderer/fixture controlado do v1;
- tracking é memória de processo;
- persistência temporal em PostgreSQL e rastreabilidade histórica pertencem à FASE 4;
- nenhuma integração externa faz parte do v1.

---

## FASE 4 — TEMPORAL MEMORY MVP — ✅ PASS

### Objetivo
Persistir a evolução temporal do gráfico com integridade e rastreabilidade.

### Entregas concluídas
- `sessions`;
- `frames`;
- `observations`;
- `candles`;
- timestamps timezone-aware normalizados para UTC;
- deduplicação persistente;
- fechamento de candle persistido;
- snapshots imutáveis de candle por observação;
- rastreabilidade `Frame → Observation → dado reconstruído`.

### Contrato temporal validado
- `Session` usa `session_id` como identidade persistente;
- `Frame` usa `frame_id`, sem tratar `image_hash` como identidade temporal;
- `Observation` referencia o `Frame` da mesma sessão;
- candle canônico usa `(session_id, open_time)` como identidade no v1;
- candle aberto pode evoluir sem duplicação;
- `high` não regride e `low` não regride em sentido incompatível com a evolução temporal;
- candle pode transitar de aberto para fechado;
- candle fechado é imutável;
- snapshots históricos são preservados e auditáveis;
- divergências/regravações incompatíveis produzem erro explícito.

### Gate — PASS
Os critérios oficiais foram comprovados em PostgreSQL real:
- replays repetidos não corrompem dados;
- candles não são duplicados dentro da mesma sessão;
- dados históricos não são sobrescritos silenciosamente.

### Evidência de fechamento
- branch `phase-4-temporal-memory-mvp`;
- HEAD técnico `4e87314e7711464d3f08841c594330ecd235bd46`;
- PR `#7 — feat: complete Phase 4 Temporal Memory MVP` — merged;
- merge funcional em `main` `f0fac60c1ba0f24ddee7ed76f512600070acdf60`;
- CI técnico da branch: run `#69` / `31438663542` — SUCCESS;
- CI do PR: run `#70` / `31438809722` — SUCCESS;
- CI pós-merge: run `#71` / `31438952349` — SUCCESS;
- suíte backend no job sem PostgreSQL: `47 passed, 31 skipped`; os testes PostgreSQL são executados separadamente;
- suíte PostgreSQL real da FASE 4: `31 passed`;
- migrations Alembic `0001 → 0002 → 0003 → 0004`, downgrade até base e re-upgrade — SUCCESS;
- `ruff check app` — SUCCESS;
- `npm run build` — SUCCESS;
- stack Docker e health checks — SUCCESS.

### Critérios de aceite verificados
- repetição determinística do histórico preserva um único candle canônico e não regride estado final;
- PK `(session_id, open_time)` impede duplicação de candle na sessão;
- snapshots imutáveis preservam o que cada frame/observação reconstruiu;
- mesmo timestamp lógico com reconstrução divergente é rejeitado;
- alterações incompatíveis depois do fechamento são rejeitadas;
- teste arquitetural mantém domínio/contrato de storage independentes de SQLAlchemy/PostgreSQL.

### Revisão de escopo no fechamento da FASE 4
Não foram implementados direção, amplitude, retorno, volatilidade, HH/HL/LH/LL, tendência, lateralização ou qualquer outro `MarketFeatures` durante a FASE 4. A FASE 5 permaneceu separada naquele fechamento.

### Decisões
Nenhuma nova decisão arquitetural foi necessária; as decisões existentes de banco temporal estruturado e PostgreSQL continuam suficientes.

---

## FASE 5 — MARKET FEATURES MVP — 🟡 IN PROGRESS

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

### Estado operacional
O lifecycle de início da FASE 5 já foi executado/revalidado e a fase está aberta na branch `phase-5-market-features-mvp`.

Progresso técnico já existente:
- primitive point-in-time `get_candles_as_of(session_id, as_of)`;
- especificação canônica em `docs/market_features.md`;
- direção;
- amplitude;
- retorno;
- volatilidade simples;
- HH — Higher High.

Pendente dentro da FASE 5:
- HL;
- LH;
- LL;
- tendência básica;
- lateralização básica.

Último incremento técnico aprovado:
- HEAD `b0b1f6d30423d01e6bbadbe0e3f25df66c52c334`;
- CI run `#91` / `31457654795` — SUCCESS.

O fechamento formal continua pendente. FASE 5 não é PASS e FASE 6 não está autorizada enquanto não houver conclusão do escopo, testes/CI/aceite finais e `chartvision-phase-close = PASS`.

---

## FASE 6 — ANALYSIS LAB MVP — 🔒 BLOCKED

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

### Bloqueio
Aguarda `PHASE_CLOSE = PASS` da FASE 5. Nenhuma implementação da FASE 6 está autorizada durante a FASE 5.

---

## FASE 7 — OUTCOME EVALUATION MVP — 🔒 BLOCKED

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

### Bloqueio
Aguarda PASS sequencial da FASE 6.

---

## FASE 8 — DASHBOARD MVP — 🔒 BLOCKED

### Objetivo
Disponibilizar uma interface única para observação e auditoria do laboratório.

### Tela única
Deve apresentar gráfico, estado do replay, qualidade visual, estado estrutural, confiança, observações e métricas.

### Fora desta fase
Não criar páginas extras, multiusuário, notificações ou integrações externas.

### Bloqueio
Aguarda PASS sequencial da FASE 7.

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
