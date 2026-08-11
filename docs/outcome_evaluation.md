# ChartVision Core — Outcome Evaluation MVP

## Status

**FASE 7 — OUTCOME EVALUATION MVP: ⬜ PENDING / CONTRATO DEFINIDO**

Este documento define o contrato funcional canônico da FASE 7.

A existência desta especificação **não inicia implementação**, não marca a FASE 7 como PASS e não desbloqueia a FASE 8. Antes de qualquer código funcional, o chat dedicado da FASE 7 deve reexecutar `.agents/skills/chartvision-phase-start/SKILL.md` e obter `PHASE_START = READY` contra o estado atual do GitHub.

---

# 1. Objetivo

Avaliar, de forma determinística e auditável, uma `Analysis` já registrada contra o que ocorreu posteriormente no Ground Truth do replay, preservando integralmente o registro histórico original e impedindo que a definição do target seja escolhida depois de observar o futuro.

Fluxo canônico:

```text
Session / experimento
        │
        ├── replay_cursor_time — operacional / rebobinável
        │
        └── session_exposure_watermark — monotônico / não rebobinável
                         │
                         ▼
OutcomeEvaluationPolicy
configuração comprometida e imutável
bound_at = exposure watermark no registro
        │
        │ policy.bound_at <= Analysis.timestamp
        ▼
Analysis registrada em T
        │
        │ imutável
        ▼
futuro ocorre
        │
        ▼
OutcomeEvaluationService
        │
        ├── StorageProvider → Analysis + Policy
        └── GroundTruthProvider → janela futura autorizada
                         │
                         ▼
                  OutcomeEvaluator
                         │
                         ▼
                      Outcome
                         │
                         ▼
                  StorageProvider
                         │
                         ▼
          métricas por policy homogênea
```

A FASE 7 não reclassifica o passado. Ela adiciona uma avaliação posterior vinculada à `Analysis` original e à policy experimental que já estava comprometida sob uma fronteira de exposição **não rebobinável**.

---

# 2. Princípios normativos

1. `Analysis.timestamp == T` continua sendo a fronteira da análise histórica.
2. A `Analysis` persistida é imutável.
3. O `AnalysisEngine` continua proibido de acessar Ground Truth, ReplaySource ou informação posterior a `T`.
4. Somente a camada de Outcome Evaluation pode consultar Ground Truth posterior, e apenas para avaliar uma `Analysis` já registrada.
5. A definição do target (`horizon_closed_candles` + `realized_return_threshold`) deve estar comprometida em uma `OutcomeEvaluationPolicy` imutável antes da Analysis elegível.
6. `OutcomeEvaluationService` não aceita configuração arbitrária escolhida no instante de avaliação `E`.
7. O cursor operacional do replay é rebobinável e **não pode** ser usado isoladamente como prova temporal de precommit.
8. Cada sessão/experimento possui uma fronteira de exposição monotonicamente não decrescente (`session_exposure_watermark`) que nunca é reduzida por reset, pause/resume ou reexecução abaixo do máximo já exposto.
9. `OutcomeEvaluationPolicy.bound_at` captura a fronteira não rebobinável da sessão no momento do compromisso.
10. O resultado realizado possui somente `UP`, `DOWN` ou `SIDEWAYS`.
11. `UNCERTAIN` pertence exclusivamente ao lado da previsão/`Analysis` e significa abstention.
12. Nenhum Outcome é criado enquanto o horizonte comprometido não estiver integralmente disponível.
13. O fim do dataset não autoriza encurtar o horizonte.
14. Dados ausentes não são inventados.
15. Métricas agregadas somente são válidas dentro de um cohort homogêneo de uma única policy.
16. O domínio de avaliação deve permanecer determinístico e independente de infraestrutura.

---

# 3. Contratos de domínio

## 3.1 `RealizedState`

O estado futuro observado possui exatamente três valores:

```text
UP
DOWN
SIDEWAYS
```

`UNCERTAIN` **não** é `RealizedState`.

## 3.2 `OutcomeConfig`

`OutcomeConfig` é o valor imutável que define o target de avaliação:

```text
horizon_closed_candles: int
realized_return_threshold: Decimal
```

Validações normativas:

```text
horizon_closed_candles >= 1
realized_return_threshold é Decimal finito
realized_return_threshold >= 0
```

Valores booleanos não satisfazem conceitualmente o contrato de inteiro do horizonte.

Não existem defaults silenciosos.

**Regra crítica:** `OutcomeConfig` não é uma escolha livre em `OutcomeEvaluationService.evaluate(...)`. No MVP, os seus valores entram na avaliação exclusivamente através da `OutcomeEvaluationPolicy` previamente comprometida da sessão.

## 3.3 Replay cursor e Session Exposure Watermark

A FASE 7 distingue obrigatoriamente dois conceitos temporais que não podem ser tratados como equivalentes.

### Replay cursor

O cursor representa a posição operacional corrente do replay:

```text
replay_cursor_time
```

Ele pode:

- avançar;
- pausar e continuar;
- ser rebobinado por `reset`;
- voltar ao início/estado sem `current_time` no comportamento vigente da FASE 1.

Portanto:

```text
replay_cursor_time
≠
prova de que instantes posteriores nunca foram observados antes
```

O cursor é adequado para controlar a reprodução corrente, mas **não é autoridade suficiente para provar precommit experimental**.

### Session Exposure Watermark

Cada sessão/experimento possui conceitualmente:

```text
session_exposure_watermark
```

Semântica normativa:

```text
session_exposure_watermark
=
maior instante lógico do mercado
que já foi exposto nessa sessão/experimento
```

A fronteira é monotonicamente não decrescente:

```text
W_new >= W_old
```

Quando a sessão expõe um instante lógico `C` superior ao máximo anterior:

```text
W_new = max(W_old, C)
```

Uma exposição inclui o avanço lógico do replay tornado observável no contexto da sessão, inclusive o tempo lógico usado para liberar/representar o estado visível. O watermark registra somente a fronteira temporal; ele não carrega OHLC, features ou resultado futuro.

### Origem antes da primeira exposição

O contrato não deixa `bound_at` indefinido quando nenhuma observação de mercado ocorreu ainda.

Cada sessão possui uma origem lógica determinística e timezone-aware:

```text
session_origin_time
```

Ela vem da configuração/metadado temporal autoritativo da sessão/replay e não é fornecida retroativamente pelo chamador. No replay controlado v1, corresponde à origem lógica determinística da reprodução.

Antes de qualquer avanço/exposição, o estado auditável usa essa origem como baseline:

```text
session_exposure_watermark = session_origin_time
```

Esse baseline não significa que um OHLC ou candle futuro foi fornecido à Analysis; ele apenas estabelece a menor fronteira temporal auditável possível da sessão e garante binding determinístico desde o início.

### Reset, pause/resume e novos ciclos

`reset` pode rebobinar o cursor operacional, mas não a memória de exposição:

```text
Replay reset
→ replay_cursor_time pode voltar ao início
→ session_exposure_watermark permanece W
```

Exemplo:

```text
avanço até 10:30
cursor = 10:30
watermark = 10:30

reset
cursor = início / estado inicial
watermark = 10:30

novo avanço até 10:15
cursor = 10:15
watermark = 10:30

novo avanço até 10:45
cursor = 10:45
watermark = 10:45
```

Também:

- `pause` não reduz watermark;
- `resume` não reduz watermark;
- `stop` não reduz watermark;
- repetir vários ciclos de replay na mesma sessão não reinicializa watermark;
- somente uma **nova sessão/experimento explicitamente criada** possui origem/watermark próprios.

`reset` operacional **não cria silenciosamente uma nova sessão/experimento** e não reabre a fronteira experimental de precommit.

## 3.4 `OutcomeEvaluationPolicy`

`OutcomeEvaluationPolicy` representa o precommit auditável da definição de Outcome para uma sessão/experimento.

Campos conceituais mínimos:

```text
policy_id: str
session_id: str
horizon_closed_candles: int
realized_return_threshold: Decimal
bound_at: datetime
```

Semântica:

- `policy_id` identifica inequivocamente a policy;
- `session_id` determina o experimento ao qual ela pertence;
- horizonte e threshold formam a configuração imutável comprometida;
- `bound_at` é uma cópia imutável da fronteira de exposição não rebobinável da sessão no instante em que a policy foi registrada.

### Regra de captura de `bound_at`

`bound_at` **não pode ser um timestamp retroativo arbitrariamente fornecido pelo chamador** e **não pode derivar exclusivamente do cursor atual rebobinável**.

A operação futura de registro deve ler a fronteira autoritativa e durável da sessão:

```text
W = session_exposure_watermark
register_policy(...)
→ policy.bound_at = W
```

É proibido:

```text
observar futuro
→ reset
→ cursor volta ao início
→ registrar policy usando cursor rebobinado
```

O reset não altera `W`; portanto a policy registrada após reset continua capturando o maior instante lógico já exposto na sessão.

Se registro de policy e avanço/exposição puderem concorrer, a implementação futura deve estabelecer uma ordem consistente entre a atualização monotônica do watermark e a captura de `bound_at`. Uma policy nunca pode capturar um watermark inferior a uma exposição que já ocorreu na mesma sessão.

Essa regra não expõe OHLC/Ground Truth ao `AnalysisEngine`; utiliza somente metadado temporal de auditoria da sessão.

### Cardinalidade MVP

Para manter o menor contrato suficiente:

```text
Session 1 → 0..1 OutcomeEvaluationPolicy
```

Uma sessão do MVP possui no máximo uma policy de Outcome Evaluation.

Consequências:

- não há ambiguidade sobre qual policy pertence a uma Analysis da sessão;
- alteração de horizonte/threshold exige nova sessão/experimento no MVP;
- múltiplas policies ou revisões de policy dentro da mesma sessão são `FUTURE` e exigem nova decisão arquitetural;
- `reset` não pode ser usado como substituto de nova sessão para escolher outro target.

### Elegibilidade temporal de uma Analysis

Para uma `Analysis` com:

```text
Analysis.session_id = S
Analysis.timestamp = T
```

ela somente é elegível para Outcome se existir a policy única da sessão `S` e:

```text
policy.session_id == Analysis.session_id
policy.bound_at <= Analysis.timestamp
```

A comparação é **inclusiva**.

Se:

```text
T == policy.bound_at
```

a Analysis pode ser elegível, sujeito aos demais contratos, porque o compromisso foi feito sem que a sessão tivesse exposto instante lógico posterior a `T`.

Se:

```text
T < policy.bound_at
```

essa policy é tardia para aquela Analysis e a avaliação deve ser rejeitada explicitamente.

Exemplo após reset:

```text
watermark histórico W = 10:30
reset
policy registrada → bound_at = 10:30

Analysis T = 10:20
→ inelegível

Analysis T = 10:30
→ temporalmente elegível, se os demais contratos forem satisfeitos

Analysis T = 10:40
→ temporalmente elegível, se os demais contratos forem satisfeitos
```

Uma Analysis anterior à fronteira máxima já exposta **não pode receber Outcome retroativamente** escolhendo horizonte/threshold depois que seu futuro já foi observado.

### Imutabilidade e idempotência

Policy é append-only no MVP. Não existe UPDATE semântico.

```text
mesmo policy_id + mesmos dados completos
→ idempotente

mesmo policy_id + qualquer dado diferente
→ conflito explícito

mesmo session_id + outra policy diferente
→ conflito explícito no MVP
```

Erro conceitual:

```text
OutcomeEvaluationPolicyConflictError
```

## 3.5 `Outcome`

`Outcome` representa uma avaliação posterior imutável de exatamente uma `Analysis`, produzida por exatamente uma `OutcomeEvaluationPolicy`.

Campos conceituais mínimos:

```text
analysis_id: str
policy_id: str

evaluation_timestamp: datetime

reference_candle_open_time: datetime
reference_candle_close_time: datetime
reference_close: Decimal

final_candle_open_time: datetime
final_candle_close_time: datetime
final_close: Decimal

horizon_closed_candles: int
realized_return_threshold: Decimal
realized_return: Decimal
realized_state: RealizedState

evidence: tuple[str, ...]
```

### Identidade

No MVP, `analysis_id` permanece simultaneamente:

- identidade lógica do Outcome;
- chave estrangeira obrigatória para `Analysis`;
- garantia de cardinalidade máxima `Analysis 1 → 0..1 Outcome`.

`policy_id` não substitui a identidade do Outcome; ele identifica o target experimental que produziu aquele Outcome.

### Invariantes

1. `analysis_id` deve referenciar uma `Analysis` existente;
2. `policy_id` deve referenciar uma `OutcomeEvaluationPolicy` existente;
3. `policy.session_id == Analysis.session_id`;
4. `policy.bound_at <= Analysis.timestamp`;
5. `Outcome.horizon_closed_candles == policy.horizon_closed_candles`;
6. `Outcome.realized_return_threshold == policy.realized_return_threshold`;
7. todos os timestamps devem ser timezone-aware;
8. `reference_candle_close_time <= Analysis.timestamp`;
9. o candle de referência deve ser o último candle Ground Truth fechado válido em ou antes de `Analysis.timestamp`;
10. `final_candle_close_time > Analysis.timestamp`;
11. o candle final deve ser exatamente o `horizon_closed_candles`-ésimo candle Ground Truth fechado após a referência;
12. referência e candle final devem pertencer à mesma sessão/contexto da Analysis;
13. `reference_close != 0`;
14. `evaluation_timestamp == final_candle_close_time`;
15. `realized_return_threshold >= 0`;
16. `realized_return` deve ser reproduzível a partir de `reference_close` e `final_close` pela fórmula canônica;
17. `realized_state` deve corresponder exatamente à regra de classificação realizada;
18. `evidence` deve ser determinística, ordenada e auditável;
19. nenhum campo do Outcome pode provocar alteração da `Analysis` vinculada;
20. policy e Outcome não podem divergir silenciosamente em identidade/configuração.

### Evidence

A evidence deve utilizar tokens determinísticos, sem texto livre variável. Ordem canônica mínima:

```text
1. OUTCOME_RULE
2. ANALYSIS_ID
3. POLICY_ID
4. REFERENCE_CANDLE_OPEN_TIME
5. REFERENCE_CANDLE_CLOSE_TIME
6. REFERENCE_CLOSE
7. FINAL_CANDLE_OPEN_TIME
8. FINAL_CANDLE_CLOSE_TIME
9. FINAL_CLOSE
10. HORIZON_CLOSED_CANDLES
11. REALIZED_RETURN_THRESHOLD
12. REALIZED_RETURN
13. REALIZED_STATE
```

A evidence do Outcome não substitui nem reescreve `Analysis.evidence`.

---

# 4. Relação Session Exposure → Policy → Analysis → Outcome

Cardinalidade canônica do MVP:

```text
Session 1
   │
   ├── replay cursor (rebobinável)
   └── exposure watermark (monotônico)
              ↓
0..1 OutcomeEvaluationPolicy
              ↓
0..N Analysis elegíveis
              ↓
0..1 Outcome por Analysis
```

A policy não é gravada dentro da `Analysis` e não exige alteração retrospectiva do modelo de Analysis.

O vínculo é derivado e auditável por:

```text
Analysis.session_id == policy.session_id
AND
policy.bound_at <= Analysis.timestamp
```

Como existe no máximo uma policy por sessão no MVP, esse vínculo é unívoco.

O Outcome registra `policy_id` e copia horizonte/threshold para auditoria. Esses valores copiados devem ser exatamente iguais aos da policy.

O exposure watermark pertence ao estado auditável da sessão/experimento; não é parte da Analysis e não é uma Market Feature.

---

# 5. Contrato temporal

## 5.1 Instantes

Para uma `Analysis` persistida:

```text
Analysis.timestamp = T
```

A avaliação recebe ainda um corte temporal explícito:

```text
evaluation_as_of = E
```

`E` representa o instante lógico até o qual o módulo de avaliação está autorizado a observar Ground Truth.

Para a policy:

```text
policy.bound_at = B
```

Para a sessão:

```text
session_exposure_watermark = W
```

No instante de registro:

```text
B = W
```

Regras:

```text
B, T, E e W devem ser timezone-aware
B <= T <= E
W nunca diminui durante a vida da sessão
```

`T` continua sendo o timestamp da Analysis; `E` é o corte de avaliação. `B` não vem de `datetime.now()` nem do cursor rebobinado: é a cópia do watermark autoritativo da sessão no compromisso.

## 5.2 Precommit e hindsight bias

A sequência obrigatória é:

```text
exposure watermark corrente = W
        ↓
policy registrada em B = W
        ↓
B <= T
        ↓
Analysis(T)
        ↓
futuro após T
        ↓
Outcome Evaluation(E)
```

É proibido:

```text
futuro conhecido até W
        ↓
reset do replay
        ↓
cursor volta para tempo < W
        ↓
escolher novo H ou threshold para Analysis(T < W)
        ↓
Outcome
```

O reset não reduz W. Portanto a nova policy, se ainda não existir policy na sessão, captura `B = W` e a Analysis anterior permanece inelegível.

Se a sessão não possuía policy elegível para `T`, a Analysis não se torna retroativamente elegível por reset ou por criação posterior de policy.

## 5.3 Candle de referência

O candle Ground Truth de referência é:

```text
reference =
último candle Ground Truth fechado
cujo close_time <= T
```

Se não existir candle de referência válido em ou antes de `T`, a avaliação retorna estado explícito de indisponibilidade e **não cria Outcome**.

## 5.4 Horizonte futuro

Seja:

```text
H = policy.horizon_closed_candles
```

Após a referência, selecionar os próximos `H` candles Ground Truth fechados em ordem temporal crescente.

O horizonte conta candles fechados efetivamente existentes. Não sintetizar gaps, não preencher intervalos ausentes e não encurtar o horizonte.

O candle final é:

```text
final_candle = H-ésimo candle fechado após reference
```

A avaliação só está disponível se:

```text
final_candle.close_time <= E
```

## 5.5 Estados de disponibilidade

A orquestração deve representar explicitamente pelo menos:

```text
AVAILABLE
PENDING_HORIZON
UNAVAILABLE_POLICY
POLICY_BOUND_TOO_LATE
UNAVAILABLE_REFERENCE
UNAVAILABLE_END_OF_DATASET
```

### `AVAILABLE`

Existe policy elegível, referência válida, existem exatamente `H` candles futuros fechados necessários e o candle final já está autorizado por `E`.

Somente neste estado o `OutcomeEvaluator` pode produzir e persistir `Outcome`.

### `PENDING_HORIZON`

Existe policy elegível e referência válida, porém menos de `H` candles futuros necessários estão disponíveis até `E`, e a fonte ainda não atingiu estado terminal para a sessão.

Resultado:

```text
nenhum Outcome
operação pode ser repetida posteriormente
```

### `UNAVAILABLE_POLICY`

Não existe policy para a sessão.

Resultado:

```text
nenhum Outcome
não é permitido escolher OutcomeConfig em E
```

### `POLICY_BOUND_TOO_LATE`

Existe policy para a sessão, porém:

```text
policy.bound_at > Analysis.timestamp
```

Resultado:

```text
nenhum Outcome para aquela Analysis
nenhuma associação retroativa
```

Esse status continua válido depois de qualquer reset, porque `bound_at` foi capturado da fronteira não rebobinável.

### `UNAVAILABLE_REFERENCE`

Não existe candle Ground Truth fechado válido em ou antes de `T`.

Resultado: nenhum Outcome.

### `UNAVAILABLE_END_OF_DATASET`

A fonte chegou ao fim definitivo da sessão/dataset e existem menos de `H` candles fechados após a referência.

Resultado:

```text
nenhum Outcome
horizonte não é reduzido
```

Análises sem Outcome por ausência/policy tardia, indisponibilidade de referência, horizonte pendente ou fim de dataset não entram nas métricas de análises avaliadas.

## 5.6 Entradas temporais inválidas

Devem falhar explicitamente, sem persistência:

- `B`, `T`, `E`, origem ou watermark naive;
- `E < T`;
- Ground Truth com timestamps naive;
- janela fora da sessão da Analysis;
- referência com `close == 0`;
- dados Ground Truth estruturalmente inconsistentes;
- policy de outra sessão;
- tentativa de usar policy tardia para aquela Analysis;
- tentativa de fornecer configuração ad hoc na avaliação;
- tentativa de diminuir o exposure watermark;
- tentativa de usar cursor rebobinado como substituto de watermark para registrar policy.

---

# 6. Ground Truth boundary

## 6.1 Contrato dedicado

A FASE 7 introduz conceitualmente um contrato de leitura exclusivo da camada de avaliação:

```text
GroundTruthProvider
```

Contrato conceitual mínimo:

```text
get_evaluation_window(
    session_id,
    analysis_timestamp,
    evaluation_as_of,
    horizon_closed_candles,
) -> GroundTruthWindow
```

`horizon_closed_candles` é obtido da policy previamente carregada; não é uma escolha livre do chamador em `E`.

`GroundTruthWindow` deve expor somente o mínimo necessário:

```text
reference_candle: Candle | None
future_closed_candles: tuple[Candle, ...]  # no máximo H
source_exhausted: bool
```

Regras do provider:

1. retornar somente candles Ground Truth fechados;
2. não retornar candle com `close_time > evaluation_as_of`;
3. retornar no máximo uma referência + `H` candles futuros;
4. ordenar deterministicamente por tempo;
5. preservar isolamento de sessão;
6. informar se a fonte atingiu fim definitivo para distinguir `PENDING_HORIZON` de `UNAVAILABLE_END_OF_DATASET`;
7. não fornecer Ground Truth ao `AnalysisEngine`, `AnalysisLabService`, FeatureEngine ou pipeline visual.

A implementação concreta do provider pode adaptar o replay controlado, mas o domínio de Outcome não deve depender diretamente de `ReplaySource`.

## 6.2 Watermark não é Ground Truth de features

O `session_exposure_watermark` contém somente um timestamp de fronteira já exposta.

Ele não fornece:

- OHLC;
- direção;
- preço;
- retorno;
- tendência;
- lateralização;
- realized state;
- qualquer feature de mercado.

É proibido fornecê-lo como atalho para inferir mercado ao `AnalysisEngine`, `AnalysisLabService`, FeatureEngine ou pipeline visual.

Seu único papel nesta fase é auditar a fronteira temporal de precommit e impedir backdating por reset.

## 6.3 Fluxos permitidos e proibidos

Permitido:

```text
Session exposure watermark
        ↓
OutcomeEvaluationPolicy
        ↓
Analysis persistida
        ↓
Replay/Ground Truth
        ↓
GroundTruthProvider
        ↓
OutcomeEvaluationService
        ↓
OutcomeEvaluator
```

Proibido:

```text
Ground Truth
    ↓
AnalysisEngine
```

```text
Ground Truth
    ↓
AnalysisLabService
```

```text
Outcome futuro
    ↓
UPDATE Analysis
```

```text
Ground Truth conhecido
    ↓
escolher Policy/OutcomeConfig retroativamente
```

```text
reset
    ↓
cursor rebobinado
    ↓
backdate policy.bound_at
```

---

# 7. Fronteira contra future leakage e hindsight bias

A distinção normativa é:

```text
SESSION EXPOSURE WATERMARK W
monotônico
não rebobina com reset
        ↓

POLICY EM B = W
compromete H e threshold
B <= T
imutável
        ↓

ANALYSIS EM T
usa somente informação <= T
é persistida
é imutável
        ↓ tempo

OUTCOME EVALUATION EM E
pode observar somente o Ground Truth necessário
com close_time <= E
usa a policy já comprometida
        ↓

OutcomeEvaluator
adiciona Outcome
nunca reescreve Analysis
```

Adicionar novos candles futuros, completar o horizonte ou avançar o replay pode:

- aumentar o exposure watermark da sessão;
- alterar `PENDING_HORIZON` para `AVAILABLE` para uma policy/Analysis já elegíveis;
- permitir a criação de Outcome quando o horizonte estiver disponível.

Isso **não pode** alterar:

- `Analysis(T)`;
- a policy;
- `policy.bound_at`;
- horizonte;
- threshold;
- confidence histórica;
- o watermark para um valor inferior depois de reset.

Um teste de regressão da FASE 6 deve continuar comprovando que adicionar futuro não altera `Analysis(T)`.

---

# 8. Estado realizado e política numérica

Com:

```text
P0 = reference_close
P1 = final_close
```

O retorno realizado é:

```text
realized_return = (P1 - P0) / P0
```

`P0 == 0` é Ground Truth inválido e deve falhar explicitamente.

Política numérica:

- `reference_close`, `final_close`, threshold e retorno usam `Decimal`;
- divisões usam `localcontext()` com precisão 28;
- arredondamento: `ROUND_HALF_EVEN`;
- não usar `float` no retorno realizado;
- não aplicar `quantize` silencioso.

Seja:

```text
R = realized_return
D = policy.realized_return_threshold
```

Regra exata:

```text
R > D   → UP
R < -D  → DOWN
senão   → SIDEWAYS
```

Logo:

```text
R == D  → SIDEWAYS
R == -D → SIDEWAYS
```

Com `D == 0`, somente retorno exatamente zero é `SIDEWAYS`.

---

# 9. Predicted state e `UNCERTAIN`

```text
predicted_state = Analysis.market_state
```

Predição:

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

`UNCERTAIN` significa abstention.

Regras:

1. participa do total de análises avaliadas se existir Outcome correspondente;
2. nunca pode ser `realized_state`;
3. aparece como coluna de previsão da confusion matrix;
4. possui `uncertain_count` e `uncertain_frequency`;
5. coverage mede a fração de previsões não-`UNCERTAIN`;
6. nunca conta como acerto de accuracy;
7. não possui precision própria;
8. quando o realizado é `C`, conta como falso negativo de `C` e reduz `recall(C)`;
9. não entra no denominador de precision de `UP`, `DOWN` ou `SIDEWAYS`.

---

# 10. Metrics Cohort — target homogêneo

Uma unidade métrica válida continua sendo:

```text
(Analysis, Outcome)
```

com:

```text
Outcome.analysis_id == Analysis.analysis_id
```

Porém um **Metric Report** possui obrigatoriamente uma única identidade de target:

```text
Metrics Cohort = exatamente um policy_id
```

Para um relatório de policy `P`:

```text
para todo Outcome O do cohort:
O.policy_id == P.policy_id
O.horizon_closed_candles == P.horizon_closed_candles
O.realized_return_threshold == P.realized_return_threshold
```

Misturar policies diferentes na mesma agregação é proibido.

A camada de métricas deve escolher a solução mínima:

```text
receber policy + pares já filtrados
```

ou validar estritamente que todos os pares possuem o mesmo `policy_id` e configuração.

No MVP canônico, entrada mista deve **falhar explicitamente**, não ser particionada silenciosamente.

Erro conceitual:

```text
MixedOutcomePolicyError
```

O relatório métrico deve expor pelo menos:

```text
policy_id
horizon_closed_candles
realized_return_threshold
```

além das métricas calculadas.

Defina:

```text
N = quantidade total de pares avaliados do mesmo policy_id
```

Análises sem Outcome não entram em `N`.

A introdução do exposure watermark **não altera** a fronteira de cohort. `BLOCKER-14` permanece resolvido pelo requisito de um único `policy_id` por relatório.

---

# 11. Confusion matrix

A matriz possui orientação fixa:

```text
LINHAS  = realized_state
COLUNAS = predicted_state
```

Ordem das linhas:

```text
[UP, DOWN, SIDEWAYS]
```

Ordem das colunas:

```text
[UP, DOWN, SIDEWAYS, UNCERTAIN]
```

```text
M[r, p] = quantidade de pares do cohort homogêneo
          com realized_state == r
          e predicted_state == p
```

A soma das 12 células deve ser exatamente `N`.

---

# 12. Accuracy

```text
correct = M[UP,UP] + M[DOWN,DOWN] + M[SIDEWAYS,SIDEWAYS]
accuracy = correct / N
```

`UNCERTAIN` está no denominador e nunca no numerador.

Se `N == 0`:

```text
accuracy = None
```

---

# 13. Precision por classe

Para:

```text
C ∈ {UP, DOWN, SIDEWAYS}
```

```text
precision(C) = M[C,C] / sum(M[r,C] para r em {UP,DOWN,SIDEWAYS})
```

Denominador zero:

```text
precision(C) = None
```

Não existe `precision(UNCERTAIN)` no MVP.

---

# 14. Recall por classe

```text
recall(C) = M[C,C] / sum(M[C,p] para p em {UP,DOWN,SIDEWAYS,UNCERTAIN})
```

Assim, `UNCERTAIN` reduz recall da classe realizada.

Denominador zero:

```text
recall(C) = None
```

---

# 15. Coverage e `UNCERTAIN`

```text
uncertain_count = sum(M[r,UNCERTAIN] para r em {UP,DOWN,SIDEWAYS})
non_uncertain_count = N - uncertain_count
coverage = non_uncertain_count / N
uncertain_frequency = uncertain_count / N
```

Quando `N > 0`:

```text
coverage + uncertain_frequency == 1
```

Se `N == 0`:

```text
uncertain_count = 0
coverage = None
uncertain_frequency = None
```

---

# 16. Política numérica das métricas

Contagens são inteiros.

Razões derivadas usam `Decimal`, contexto local com precisão 28 e `ROUND_HALF_EVEN`.

Denominador zero retorna `None`, nunca `0.0` inventado.

Nenhuma métrica pode alterar Analysis, Outcome, policy ou confidence persistidos.

---

# 17. Confidence calibration no MVP

## 17.1 Semântica

`Analysis.confidence` continua sendo confiança operacional rule-based, **não probabilidade estatística**.

A FASE 7 não recalibra nem reescreve confidence. Produz somente diagnóstico empírico da relação entre confidence registrada e acerto posteriormente observado.

## 17.2 Cohort obrigatório

Confidence calibration é calculada **somente dentro de um único `policy_id`**.

É proibido combinar no mesmo `weighted_alignment_gap` Outcomes de policies, horizons ou thresholds diferentes.

Dentro do cohort homogêneo, entram somente previsões:

```text
UP
DOWN
SIDEWAYS
```

`UNCERTAIN` é excluído da calibração.

Defina:

```text
Nc = quantidade de pares não-UNCERTAIN do mesmo policy_id
```

## 17.3 Conversão e bins

```text
confidence_decimal = Decimal(str(Analysis.confidence))
```

Confidence deve estar em `[0,1]`.

Bins canônicos:

```text
B1 = [0.0, 0.2)
B2 = [0.2, 0.4)
B3 = [0.4, 0.6)
B4 = [0.6, 0.8)
B5 = [0.8, 1.0]
```

`1.0` pertence ao último bin.

## 17.4 Métricas por bin

Para cada bin `b`:

```text
n_b = quantidade de pares no bin
```

Se `n_b > 0`:

```text
mean_confidence_b = soma(confidence_decimal) / n_b
observed_accuracy_b = acertos_no_bin / n_b
absolute_gap_b = abs(mean_confidence_b - observed_accuracy_b)
```

Se `n_b == 0`:

```text
mean_confidence_b = None
observed_accuracy_b = None
absolute_gap_b = None
```

## 17.5 Diagnóstico agregado

Quando `Nc > 0`:

```text
weighted_alignment_gap =
sum((n_b / Nc) * absolute_gap_b para bins não vazios)
```

Quando `Nc == 0`:

```text
weighted_alignment_gap = None
```

É diagnóstico de alinhamento operacional, não ECE probabilístico, Brier score ou prova de calibração estatística.

---

# 18. Persistência conceitual da fronteira de exposição

A informação necessária para impedir backdating por reset pertence ao estado auditável da **sessão/experimento**, não ao cursor efêmero do ReplaySource.

A implementação futura deve representar semanticamente, em `sessions` ou registro equivalente:

```text
session_id
session_origin_time
session_exposure_watermark
```

Invariantes de persistência:

- `session_origin_time` é imutável e timezone-aware;
- `session_exposure_watermark` é timezone-aware;
- `session_exposure_watermark >= session_origin_time`;
- atualizações são monotônicas: somente `max(W_old, exposed_at)` é permitido;
- não existe operação de redução de watermark;
- reset do replay não altera watermark;
- pause/resume não altera watermark para baixo;
- reexecução abaixo do máximo anterior não altera watermark;
- nova exposição acima do máximo anterior aumenta watermark;
- o estado sobrevive a reinvocação de serviço e, quando a persistência da FASE 7 for implementada, a restart de processo;
- sessões diferentes possuem watermark independente.

A persistência deve permitir auditar que a policy capturou a fronteira vigente no compromisso. O registro da policy deve usar a versão autoritativa/durável do watermark, não uma cópia stale do cursor em memória.

Esta missão de governança **não cria migration, coluna ou tabela**.

---

# 19. Persistência conceitual da Policy

A FASE 7 implementará posteriormente uma entidade/tabela conceitual:

```text
outcome_evaluation_policies
```

Esta missão de governança **não cria migration nem tabela**.

Campos mínimos:

```text
policy_id
session_id
horizon_closed_candles
realized_return_threshold
bound_at
```

Constraints conceituais mínimas:

- `policy_id` primary key;
- `session_id` FK obrigatória para `sessions.session_id`;
- `session_id` UNIQUE no MVP, garantindo no máximo uma policy por sessão;
- `horizon_closed_candles >= 1`;
- `realized_return_threshold >= 0` e finito;
- `bound_at` timezone-aware na borda de domínio;
- valores Decimal persistidos como numéricos exatos, não `float`.

`bound_at` deve ser capturado da fronteira de exposição autoritativa e não rebobinável da sessão no registro. É proibido usar `_current_time`/cursor rebobinado como prova exclusiva de precommit.

Imutabilidade:

- não existe UPDATE semântico;
- mesma identidade + mesmos dados → idempotente;
- mesma identidade + dados diferentes → `OutcomeEvaluationPolicyConflictError`;
- outra policy para a mesma sessão → conflito explícito no MVP.

---

# 20. Persistência conceitual de Outcome

A FASE 7 implementará posteriormente:

```text
outcomes
```

Campos mínimos:

```text
analysis_id
policy_id

evaluation_timestamp
reference_candle_open_time
reference_candle_close_time
reference_close
final_candle_open_time
final_candle_close_time
final_close

horizon_closed_candles
realized_return_threshold
realized_return
realized_state

evidence
```

Constraints mínimas:

- `analysis_id` primary key;
- `analysis_id` FK para `analyses.analysis_id`;
- `policy_id` FK para `outcome_evaluation_policies.policy_id`;
- FKs com política que preserve auditoria;
- `horizon_closed_candles >= 1`;
- `realized_return_threshold >= 0`;
- `realized_state` em `UP`, `DOWN`, `SIDEWAYS`;
- `reference_close != 0`;
- `final_candle_close_time > reference_candle_close_time`;
- evidence ordenada com round-trip sem perda;
- Decimal exato, não `float`.

Validações cruzadas obrigatórias na camada de domínio/orquestração e integração:

```text
policy.session_id == Analysis.session_id
policy.bound_at <= Analysis.timestamp
Outcome.policy_id == policy.policy_id
Outcome.horizon_closed_candles == policy.horizon_closed_candles
Outcome.realized_return_threshold == policy.realized_return_threshold
```

Não existe UPDATE semântico de Outcome no MVP.

Métricas agregadas continuam derivadas; não há tabela persistente de métricas no MVP.

---

# 21. Identidade, idempotência e reavaliação

Policy:

```text
identity = policy_id
Session 1 → 0..1 Policy
```

Outcome:

```text
identity = analysis_id
Analysis 1 → 0..1 Outcome
```

Outcome idempotência:

```text
mesmo analysis_id + mesmos dados completos
→ idempotente

mesmo analysis_id + qualquer dado diferente
→ OutcomeConflictError
```

Enquanto não existe Outcome:

- `PENDING_HORIZON` pode ser reavaliado posteriormente;
- quando o horizonte fica disponível, um único Outcome pode ser criado **com a mesma policy já comprometida**.

Depois de persistido:

- mesma policy + mesmo Ground Truth → mesmo Outcome, idempotente;
- outra configuração não pode sobrescrever o Outcome;
- Ground Truth divergente para a mesma identidade produz conflito, nunca UPDATE.

Múltiplos horizons/policies simultâneos por Analysis são `FUTURE`.

Reset não altera identidade de policy/Outcome e não abre uma janela para nova policy na mesma sessão.

---

# 22. `OutcomeEvaluator`

`OutcomeEvaluator` é domínio puro.

Responsabilidades:

1. receber `Analysis` persistida/imutável;
2. receber a policy/configuração já comprometida;
3. receber candle de referência Ground Truth válido;
4. receber candle final Ground Truth válido;
5. validar invariantes;
6. calcular `realized_return`;
7. classificar `RealizedState`;
8. produzir `Outcome` determinístico com `policy_id`.

Não acessa PostgreSQL, SQLAlchemy, FastAPI, filesystem, relógio real, StorageProvider, ReplaySource, GroundTruthProvider, frontend ou Dashboard.

Propriedade:

```text
mesma Analysis
+ mesma Policy
+ mesma referência
+ mesmo candle final
=
mesmo Outcome
```

---

# 23. Orquestração

A camada conceitual é:

```text
OutcomeEvaluationService
```

Contrato canônico de avaliação:

```text
evaluate(
    analysis_id,
    evaluation_as_of,
)
```

**Não** recebe `OutcomeConfig` arbitrário e não recebe `policy_id` escolhível pelo chamador para trocar o target.

Responsabilidades:

1. carregar `Analysis` pelo `StorageProvider`;
2. rejeitar Analysis inexistente;
3. carregar a policy única por `Analysis.session_id`;
4. retornar `UNAVAILABLE_POLICY` se não existir;
5. validar `policy.bound_at <= Analysis.timestamp`;
6. retornar/rejeitar `POLICY_BOUND_TOO_LATE` se a policy for tardia;
7. obter horizonte/threshold exclusivamente da policy;
8. validar `evaluation_as_of`;
9. consultar `GroundTruthProvider.get_evaluation_window(...)` com o horizonte comprometido;
10. interpretar estados de disponibilidade;
11. chamar `OutcomeEvaluator` somente quando `AVAILABLE`;
12. persistir Outcome imutável;
13. retornar Outcome/status sem modificar Analysis ou policy.

O serviço pode depender de `StorageProvider` e `GroundTruthProvider`. `OutcomeEvaluator` não depende deles.

### Registro da policy

A futura operação de registro é separada da avaliação:

```text
register_outcome_evaluation_policy(
    session_id,
    policy_id,
    OutcomeConfig,
)
```

No registro:

1. carregar o estado auditável da sessão;
2. obter `session_exposure_watermark` autoritativo e durável;
3. capturar `bound_at = session_exposure_watermark`;
4. nunca aceitar `bound_at` fornecido pelo chamador;
5. nunca substituir watermark pelo `replay_cursor_time` corrente;
6. persistir policy imutável sob ordenação consistente com exposições da mesma sessão.

### Registro/avanço da exposição

A implementação futura precisa possuir uma operação semanticamente equivalente a:

```text
record_session_exposure(session_id, exposed_at)
→ W_new = max(W_old, exposed_at)
```

Não existe operação semântica `rewind_session_exposure_watermark`.

O reset da FASE 1 continua sendo apenas reset operacional do replay cursor.

---

# 24. Extensões futuras mínimas de `StorageProvider`

Quando a implementação da FASE 7 for autorizada, o contrato poderá ser estendido somente com o mínimo necessário para preservar a semântica:

```text
get_session_exposure_state(session_id)
record_session_exposure(session_id, exposed_at)

save_outcome_evaluation_policy(policy) -> None
get_outcome_evaluation_policy(policy_id) -> OutcomeEvaluationPolicy | None
get_outcome_evaluation_policy_for_session(session_id) -> OutcomeEvaluationPolicy | None

save_outcome(outcome) -> None
get_outcome(analysis_id) -> Outcome | None
list_outcomes(policy_id) -> tuple[Outcome, ...]
```

O nome concreto do contrato de exposição pode variar no incremento autorizado, mas deve preservar origem determinística, watermark monotônico e durabilidade suficiente para impedir backdating após reset/restart.

Erros conceituais:

```text
OutcomeEvaluationPolicyConflictError
OutcomeConflictError
```

`list_outcomes(policy_id)` é preferido no MVP porque expressa a fronteira de cohort no próprio contrato de leitura.

Mesmo assim, a camada de métricas deve validar que todo Outcome retornado possui o mesmo `policy_id` e configuração da policy carregada.

Uma implementação futura que mantenha `list_outcomes()` sem filtro só seria aceitável se agrupar/validar estritamente por `policy_id` antes de qualquer agregação; mistura silenciosa é proibida.

Ground Truth **não** deve ser incorporado ao `StorageProvider`. O exposure watermark é metadado temporal de auditoria da sessão, não OHLC/Ground Truth de avaliação.

---

# 25. Contrato das métricas

A camada de métricas deve ser pura e receber:

```text
OutcomeEvaluationPolicy
+ pares Analysis/Outcome da mesma policy
```

Ela deve validar homogeneidade antes de calcular qualquer agregado.

Não deve consultar Ground Truth, recalcular Outcome, alterar Analysis/Outcome/policy, consultar relógio, depender de PostgreSQL ou ReplaySource.

Resultado conceitual mínimo:

```text
policy_id
horizon_closed_candles
realized_return_threshold
total_evaluated
accuracy
precision_by_class
recall_by_class
confusion_matrix
coverage
uncertain_count
uncertain_frequency
confidence_calibration
```

Entrada com policies incompatíveis deve falhar com erro explícito antes de produzir resultados parciais.

O exposure watermark não participa das fórmulas métricas; ele apenas garante que o target do cohort foi comprometido sob uma fronteira temporal auditável.

---

# 26. Critérios de aceite da FASE 7

A FASE 7 somente poderá ser encerrada quando houver evidência automatizada de todos os critérios abaixo.

1. retorno acima do threshold produz `RealizedState.UP`;
2. retorno abaixo do threshold negativo produz `RealizedState.DOWN`;
3. retorno dentro da faixa produz `RealizedState.SIDEWAYS`;
4. retorno exatamente `+threshold` produz `SIDEWAYS`;
5. retorno exatamente `-threshold` produz `SIDEWAYS`;
6. configuração rejeita horizonte menor que 1;
7. configuração rejeita threshold negativo, NaN ou infinito;
8. referência é o último candle Ground Truth fechado com `close_time <= Analysis.timestamp`;
9. horizonte disponível seleciona exatamente o H-ésimo candle fechado após a referência;
10. horizonte ainda não disponível retorna `PENDING_HORIZON` e não persiste Outcome;
11. fim definitivo do dataset antes do horizonte retorna `UNAVAILABLE_END_OF_DATASET` e não encurta o horizonte;
12. ausência de referência retorna `UNAVAILABLE_REFERENCE` e não cria Outcome;
13. timestamps naive ou `evaluation_as_of < Analysis.timestamp` falham explicitamente;
14. `reference_close == 0` é rejeitado sem Outcome;
15. `Analysis` permanece semanticamente inalterada antes e depois da avaliação;
16. `AnalysisEngine` e `AnalysisLabService` permanecem sem acesso a Ground Truth/OutcomeEvaluator;
17. adicionar futuro continua sem alterar `Analysis(T)`;
18. `OutcomeEvaluator` é determinístico para mesma entrada/policy;
19. Outcome persistido realiza round-trip sem perda de Decimal, timestamps, policy_id ou evidence;
20. Outcome persistido é imutável;
21. mesma identidade de Outcome + mesmos dados é idempotente;
22. mesma identidade de Outcome + dados diferentes produz `OutcomeConflictError`;
23. confusion matrix usa linhas `[UP, DOWN, SIDEWAYS]` e colunas `[UP, DOWN, SIDEWAYS, UNCERTAIN]`;
24. accuracy usa todas as análises avaliadas do cohort no denominador e trata `UNCERTAIN` como não acerto;
25. precision por `UP`, `DOWN`, `SIDEWAYS` segue o denominador da respectiva classe e retorna `None` com denominador zero;
26. recall por `UP`, `DOWN`, `SIDEWAYS` inclui `UNCERTAIN` como falso negativo e retorna `None` com denominador zero;
27. coverage é a fração de previsões não-`UNCERTAIN`;
28. `uncertain_count` e `uncertain_frequency` obedecem às fórmulas canônicas;
29. para `N == 0`, accuracy/coverage/uncertain_frequency são `None` e contagens/matriz permanecem zero;
30. confidence calibration exclui `UNCERTAIN`, usa os cinco bins canônicos e produz estatísticas determinísticas;
31. bin vazio retorna métricas de bin `None` sem contaminar o agregado;
32. `weighted_alignment_gap` retorna `None` quando `Nc == 0`;
33. nenhuma métrica, Outcome ou avaliação altera retrospectivamente `Analysis.confidence` ou outro campo da Analysis;
34. nenhuma funcionalidade da FASE 8/Dashboard é introduzida;
35. nenhuma integração financeira, corretora, ML/RL, novos indicadores ou escopo pós-v1 é introduzido;
36. a policy/configuração é registrada sob fronteira temporal autoritativa antes da Analysis correspondente ser elegível, com `policy.bound_at <= Analysis.timestamp`;
37. policy com `bound_at > Analysis.timestamp` é rejeitada para aquela Analysis e não produz Outcome;
38. policy persistida é imutável e não admite UPDATE semântico;
39. mesma `policy_id` + mesmos dados completos é idempotente;
40. mesma `policy_id` + dados diferentes produz `OutcomeEvaluationPolicyConflictError`;
41. Outcome referencia inequivocamente a policy usada por `policy_id`;
42. Outcome não pode divergir de `horizon_closed_candles` ou `realized_return_threshold` da policy;
43. métricas de um único cohort homogêneo funcionam normalmente e expõem a policy/configuração do report;
44. mistura de Outcomes de policies diferentes falha explicitamente antes de qualquer agregação;
45. confidence calibration e `weighted_alignment_gap` nunca misturam policies/configurações;
46. tentativa de escolher novo threshold ou horizonte depois do resultado não pode redefinir target, tornar Analysis antiga elegível, sobrescrever policy nem sobrescrever Outcome;
47. `replay_cursor_time` é tratado como cursor rebobinável e não como prova exclusiva de precommit;
48. uma sessão sem exposição anterior possui `session_origin_time` determinístico/timezone-aware como baseline inicial do exposure watermark;
49. `session_exposure_watermark` é monotonicamente não decrescente durante toda a vida da sessão;
50. avanço que ultrapassa a maior exposição anterior aumenta o watermark para a nova fronteira;
51. `reset` pode rebobinar cursor/posição, mas não reduz nem reinicializa o watermark;
52. `pause` e `resume` não reduzem o watermark;
53. reexecução após reset até um instante inferior ao máximo anterior mantém o watermark anterior;
54. reexecução posterior acima do máximo anterior eleva o watermark ao novo máximo;
55. policy registrada depois de reset captura `bound_at` a partir do watermark preservado, nunca do cursor rebobinado;
56. uma Analysis com `T < session_exposure_watermark` no compromisso permanece inelegível mesmo após reset;
57. a inclusividade é exata: `T == policy.bound_at` pode ser elegível, enquanto `T < policy.bound_at` é rejeitado, sujeitos aos demais contratos;
58. reset não permite escolher retrospectivamente novo threshold/horizon para Analysis cujo futuro já estava coberto pela exposição anterior;
59. nova sessão/experimento possui origem/watermark próprios e independentes; reset da mesma sessão não equivale a nova sessão;
60. estado necessário do exposure watermark realiza round-trip/auditoria sem regressão e sobrevive conceitualmente a reinvocação/restart quando a persistência da FASE 7 existir;
61. policy continua imutável e única por sessão através de reset e múltiplos ciclos de replay;
62. Outcome continua vinculado à mesma policy e configuração independentemente de reset posterior;
63. cohorts métricos por `policy_id`, inclusive confidence calibration, permanecem homogêneos e não são alterados pelo mecanismo de watermark.

Cada critério deve possuir teste automatizado ou evidência automatizada equivalente no fechamento formal.

---

# 27. Test plan obrigatório

## 27.1 Unidade — `OutcomeConfig`

Cobrir:

```text
horizon >= 1
horizon inválido
threshold zero
threshold positivo
threshold negativo
threshold NaN/infinito
```

## 27.2 Policy/config precommit

Planejar testes para:

- policy válida registrada sob frontier elegível;
- `bound_at` capturado pelo exposure watermark da sessão, não backdatável pelo chamador;
- policy tardia rejeitada para Analysis anterior;
- ausência de policy → `UNAVAILABLE_POLICY`;
- policy imutável;
- mesma policy idempotente;
- conflito por mesma `policy_id` com dados diferentes;
- conflito por segunda policy diferente na mesma sessão;
- vínculo correto `Session → Policy → Analysis`;
- `policy.bound_at <= Analysis.timestamp`;
- igualdade `policy.bound_at == Analysis.timestamp` explicitamente aceita quando os demais contratos passam;
- tentativa de trocar threshold depois do futuro conhecido não altera target;
- tentativa de trocar horizonte depois do futuro conhecido não altera target.

## 27.3 Replay cursor / exposure watermark / reset

Cenário crítico obrigatório:

```text
start session
advance até W
observar mercado até W
reset
registrar policy
carregar/tentar avaliar Analysis em T < W
→ POLICY_BOUND_TOO_LATE / REJEITAR
→ nenhum Outcome
```

Cobrir também:

```text
advance até W
reset
advance até X onde X < W
→ watermark continua W
```

```text
advance até W
reset
advance até Y onde Y > W
→ watermark passa a Y
```

Mais testes:

- policy antes de qualquer exposição usa origem determinística da sessão;
- policy depois de exposição captura o máximo já exposto;
- cursor pode voltar ao estado inicial sem reduzir watermark;
- reset repetido não reduz watermark;
- pause/resume não reduz watermark;
- stop/restart operacional da reprodução na mesma sessão não reduz watermark;
- reexecução abaixo do máximo anterior não reduz watermark;
- nova máxima exposição atualiza watermark;
- `T == bound_at` respeita inclusividade;
- `T < bound_at` permanece inelegível após reset;
- nova sessão possui watermark independente;
- persistência/round-trip do estado de exposição preserva monotonicidade;
- reinvocação do serviço carrega o watermark durável, não cursor stale;
- tentativa explícita de diminuir watermark falha;
- ordem consistente entre exposição e registro da policy impede captura de watermark anterior a exposição já ocorrida.

## 27.4 Unidade — `OutcomeEvaluator`

Cobrir:

```text
UP acima do threshold
DOWN abaixo de -threshold
SIDEWAYS dentro da faixa
igualdade em +threshold
igualdade em -threshold
reference_close zero
sessão/contexto inconsistente
policy incompatível
timestamps inválidos
mesma entrada + mesma policy → mesmo Outcome
policy_id/evidence determinísticos
```

## 27.5 Orquestração/horizonte

Com providers fakes/determinísticos:

- serviço não aceita OutcomeConfig arbitrário na avaliação;
- serviço carrega policy pela sessão da Analysis;
- `UNAVAILABLE_POLICY`;
- `POLICY_BOUND_TOO_LATE`;
- última referência fechada `<= T`;
- H-ésimo candle futuro;
- horizonte disponível;
- `PENDING_HORIZON`;
- `UNAVAILABLE_REFERENCE`;
- `UNAVAILABLE_END_OF_DATASET`;
- não sintetizar gaps;
- não retornar candle além de `evaluation_as_of`;
- Outcome reproduz `policy_id`, horizon e threshold da policy;
- policy registration usa exposure watermark persistido, não `ReplaySource.current_time` rebobinável.

## 27.6 Arquitetura / Ground Truth

Teste arquitetural deve provar que:

- `AnalysisEngine` não importa GroundTruthProvider, ReplaySource, OutcomeEvaluator ou policy de avaliação;
- `AnalysisLabService` não consulta Ground Truth;
- pipeline visual continua isolado de Ground Truth;
- Outcome Evaluation acessa Ground Truth apenas pelo contrato autorizado;
- policy não fornece OHLC/Ground Truth ao módulo de Analysis;
- exposure watermark não é fonte de OHLC/features;
- reset do ReplaySource não é interpretado como reset do histórico experimental de exposição.

## 27.7 Regressão anti-future-leakage

Reexecutar FASE 6 para comprovar que future candle, future snapshot e evolução futura de candle conhecido não alteram `Analysis(T)`.

Adicionar cenário:

```text
Policy pré-comprometida
→ Analysis(T)
→ PENDING_HORIZON
→ futuro avança
→ AVAILABLE/Outcome
```

sem modificar Analysis ou policy.

Adicionar regressão de hindsight bias:

```text
futuro exposto até W
→ reset
→ tentativa de policy para Analysis T < W
→ rejeitada
```

sem modificar Analysis histórica.

## 27.8 Métricas / cohort

Cobrir:

- todos os Outcomes com mesma policy;
- policies diferentes detectadas;
- `MixedOutcomePolicyError` antes de agregado misto;
- confusion matrix por policy;
- accuracy por policy;
- precision por policy;
- recall por policy;
- coverage/UNCERTAIN por policy;
- matriz completa e ordem fixa;
- denominadores zero;
- `N == 0`;
- soma da matriz = N;
- `coverage + uncertain_frequency == 1` quando `N > 0`;
- reset/watermark não altera `policy_id` nem permite mistura de cohort.

## 27.9 Confidence calibration

Cobrir:

- um único policy_id por report;
- policies diferentes rejeitadas;
- cada um dos cinco bins;
- limites `0.0`, `0.2`, `0.4`, `0.6`, `0.8`, `1.0`;
- exclusão de `UNCERTAIN`;
- média de confidence;
- observed accuracy;
- absolute gap;
- weighted alignment gap;
- bins vazios;
- `Nc == 0`;
- reset/watermark não muda a policy do relatório.

## 27.10 Persistência PostgreSQL futura

Quando autorizada:

- migration cria somente estruturas necessárias da FASE 7;
- origem temporal da sessão/exposure state preservada;
- watermark monotônico persistido;
- tentativa de persistir watermark menor é rejeitada/ignorada de forma determinística sem regressão;
- reset não reduz watermark persistido;
- round-trip/restart preserva watermark;
- isolamento de watermark entre sessões;
- round-trip de policy;
- unique policy por session no MVP;
- `bound_at` preservado e igual à fronteira autoritativa capturada no registro;
- Decimal preservado;
- policy idempotente/conflito/imutável;
- round-trip Outcome com `policy_id`;
- FK Outcome→Policy e Outcome→Analysis;
- igualdade Outcome config = Policy config;
- uma linha Outcome por `analysis_id`;
- Outcome idempotente/conflito/imutável;
- `list_outcomes(policy_id)` não mistura cohorts;
- migration upgrade/downgrade/re-upgrade.

## 27.11 Regressão completa

Executar novamente os testes relevantes das FASES 1–6, especialmente:

- Replay gate temporal;
- Start/Pause/Resume/Reset e determinismo da FASE 1;
- isolamento de Ground Truth;
- Temporal Memory;
- point-in-time;
- FeatureEngine;
- AnalysisEngine;
- AnalysisLabService;
- persistência imutável de Analysis;
- regressões anti-future-leakage da FASE 6;
- cohorts/metrics da FASE 7 já especificados;
- CI completo, frontend build e Docker Compose.

A FASE 1 deve continuar comprovando sua semântica funcional de reset. O novo teste de watermark pertence à implementação futura da FASE 7 e não redefine retroativamente `ReplaySource.reset()`.

---

# 28. Resolução dos blockers de especificação

| Blocker | Resolução canônica |
|---|---|
| BLOCKER-01 — Outcome indefinido | Seções 3 e 20–21. |
| BLOCKER-02 — horizonte indefinido | Seção 5. |
| BLOCKER-03 — conversão futura para classe | Seção 8. |
| BLOCKER-04 — Ground Truth contract | Seção 6. |
| BLOCKER-05 — fronteira temporal | Seções 3.3, 5 e 7. |
| BLOCKER-06 — UNCERTAIN nas métricas | Seções 9 e 15. |
| BLOCKER-07 — fórmulas das métricas | Seções 11–16. |
| BLOCKER-08 — confidence calibration | Seção 17. |
| BLOCKER-09 — persistência | Seções 18–20. |
| BLOCKER-10 — identidade/idempotência | Seção 21. |
| BLOCKER-11 — orquestração/storage | Seções 23–25. |
| BLOCKER-12 — aceite/testes | Seções 26 e 27. |
| BLOCKER-13 — configuração escolhível após futuro / binding rebobinável | **REABERTO pelo P1 do PR #11 e corrigido** pelas Seções 3.3–3.4, 5.2, 7, 18–19, 23–24, critérios 36–42 e 47–62, e testes 27.2–27.7/27.10. `bound_at` usa exposure watermark não rebobinável; reset não permite backdating. |
| BLOCKER-14 — cohorts métricos heterogêneos | Permanece resolvido pelas Seções 10, 17.2, 24–25 e critérios 43–45/63. O mecanismo de watermark não altera a regra de um único `policy_id` por cohort. |

Os blockers são considerados resolvidos documentalmente somente após integração desta especificação ao `main` com CI verde. Isso não equivale a `PHASE_START = READY`; o Phase Start deve ser reexecutado somente quando a governança autorizar essa próxima ação.

---

# 29. Fora do escopo da FASE 7

Não implementar nesta fase:

- Dashboard / FASE 8;
- frontend de métricas;
- páginas adicionais;
- execução financeira;
- compra/venda;
- sinais operacionais;
- gestão de capital;
- corretoras/plataformas externas;
- dinheiro real;
- notícias;
- sentimento;
- novos indicadores;
- machine learning;
- reinforcement learning;
- reclassificação retroativa de Analysis;
- ajuste retroativo de confidence;
- múltiplos Outcomes por Analysis;
- múltiplas policies ou revisões de policy dentro da mesma sessão;
- múltiplos horizons/configurações por Analysis;
- tabela persistente de métricas agregadas;
- fontes externas além do replay controlado do v1.

---

# 30. Sequência permitida após novo PHASE START

Somente depois de `chartvision-phase-start = READY`, a implementação poderá ser dividida em incrementos pequenos.

A primeira missão técnica deve permanecer limitada aos contratos puros de domínio necessários ao Outcome Evaluation, à policy e à fronteira temporal de exposição já especificadas, sem antecipar persistence, API, frontend ou Dashboard salvo autorização específica do Phase Brief.

Este documento não cria essa autorização por si só.

---

# 31. Definition of Done específica

A FASE 7 exigirá, no fechamento:

```text
policy precommit com exposure watermark não rebobinável comprovado
+
reset sem backdating comprovado
+
contrato implementado
+
Outcome UP/DOWN/SIDEWAYS comprovado
+
horizonte temporal comprovado
+
Ground Truth boundary comprovada
+
Analysis imutável comprovada
+
Policy imutável/idempotente comprovada
+
Outcome imutável/idempotente comprovado
+
cohorts métricos homogêneos comprovados
+
accuracy/precision/recall/matriz comprovados
+
coverage/UNCERTAIN comprovados
+
confidence calibration por policy comprovada
+
PostgreSQL/migrations comprovados
+
regressões verdes
+
CI verde
+
documentação atualizada
+
PROJECT_STATE atualizado
+
ROADMAP atualizado
+
Issue #1 atualizada
+
chartvision-phase-close = PASS
```

Somente então a FASE 8 poderá ser autorizada.

---

# 32. Resumo normativo

```text
SESSION / EXPERIMENTO
        │
        ├── REPLAY CURSOR
        │   operacional
        │   rebobinável por reset
        │
        └── EXPOSURE WATERMARK W
            baseline = session_origin_time
            monotônico
            nunca reduz com reset
            persiste/audita máximo já exposto
                    ↓
POLICY PRECOMMIT
policy_id
H >= 1
threshold Decimal >= 0
bound_at = W no registro
imutável
uma policy por sessão no MVP
        ↓
policy.bound_at <= Analysis.timestamp
T == B permitido
T < B rejeitado
        ↓
ANALYSIS(T)
usa somente informação <= T
imutável
        ↓
futuro ocorre
        ↓
OUTCOME EVALUATION(E)
carrega policy da sessão
NÃO recebe configuração arbitrária
        ↓
GROUND TRUTH PROVIDER
reference = último fechado <= T
+ no máximo H futuros fechados <= E
        ↓
HORIZON GATE
sem H completo → nenhum Outcome
        ↓
REALIZED RETURN
(final_close - reference_close) / reference_close
        ↓
REALIZED STATE
R > D   → UP
R < -D  → DOWN
senão   → SIDEWAYS
        ↓
OUTCOME
identity = analysis_id
policy_id obrigatório
config == policy config
imutável
        ↓
METRICS COHORT
exatamente um policy_id
mistura → erro explícito
        ↓
CONFIDENCE CALIBRATION
mesmo policy_id
        ↓
FASE 8
continua bloqueada até PHASE_CLOSE = PASS
```
