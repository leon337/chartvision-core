# ChartVision Core — Outcome Evaluation MVP

## Status

**FASE 7 — OUTCOME EVALUATION MVP: ⬜ PENDING / CONTRATO DEFINIDO**

Este documento define o contrato funcional canônico da FASE 7.

A existência desta especificação **não inicia implementação**, não marca a FASE 7 como PASS e não desbloqueia a FASE 8. Antes de qualquer código funcional, o chat dedicado da FASE 7 deve reexecutar `.agents/skills/chartvision-phase-start/SKILL.md` e obter `PHASE_START = READY` contra o estado atual do GitHub.

---

# 1. Objetivo

Avaliar, de forma determinística e auditável, uma `Analysis` já registrada contra o que ocorreu posteriormente no Ground Truth do replay, preservando integralmente o registro histórico original.

Fluxo canônico:

```text
Analysis registrada em T
        │
        │ imutável
        ▼
OutcomeEvaluationService
        │
        ├── StorageProvider → Analysis
        │
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
              métricas derivadas
```

A FASE 7 não reclassifica o passado. Ela somente adiciona uma avaliação posterior vinculada à `Analysis` original.

---

# 2. Princípios normativos

1. `Analysis.timestamp == T` continua sendo a fronteira da análise histórica.
2. A `Analysis` persistida é imutável.
3. O `AnalysisEngine` continua proibido de acessar Ground Truth, ReplaySource ou informação posterior a `T`.
4. Somente a camada de Outcome Evaluation pode consultar Ground Truth posterior, e apenas para avaliar uma `Analysis` já registrada.
5. O resultado realizado possui somente `UP`, `DOWN` ou `SIDEWAYS`.
6. `UNCERTAIN` pertence exclusivamente ao lado da previsão/`Analysis` e significa abstention.
7. Nenhum Outcome é criado enquanto o horizonte configurado não estiver integralmente disponível.
8. O fim do dataset não autoriza encurtar o horizonte.
9. Dados ausentes não são inventados.
10. O domínio de avaliação deve permanecer determinístico e independente de infraestrutura.

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

A configuração da avaliação é explícita e não possui defaults silenciosos:

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

Configuração inválida deve falhar explicitamente antes de consultar ou persistir Outcome.

## 3.3 `Outcome`

`Outcome` representa uma avaliação posterior imutável de exatamente uma `Analysis`.

Campos conceituais mínimos:

```text
analysis_id: str

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

No MVP, `analysis_id` é simultaneamente:

- identidade lógica do Outcome;
- chave estrangeira obrigatória para `Analysis`;
- garantia de cardinalidade máxima `Analysis 1 → 0..1 Outcome`.

Não existe necessidade de um `outcome_id` artificial no MVP.

### Invariantes

1. `analysis_id` deve referenciar uma `Analysis` existente;
2. todos os timestamps devem ser timezone-aware;
3. `reference_candle_close_time <= Analysis.timestamp`;
4. o candle de referência deve ser o último candle Ground Truth fechado válido em ou antes de `Analysis.timestamp`;
5. `final_candle_close_time > Analysis.timestamp`;
6. o candle final deve ser exatamente o `horizon_closed_candles`-ésimo candle Ground Truth fechado após a referência;
7. referência e candle final devem pertencer à mesma sessão/contexto da Analysis;
8. `reference_close != 0`;
9. `evaluation_timestamp == final_candle_close_time`;
10. `realized_return_threshold >= 0`;
11. `realized_return` deve ser reproduzível a partir de `reference_close` e `final_close` pela fórmula canônica deste documento;
12. `realized_state` deve corresponder exatamente à regra de classificação realizada;
13. `evidence` deve ser determinística, ordenada e auditável;
14. nenhum campo do Outcome pode provocar alteração da `Analysis` vinculada.

### Evidence

A evidence deve utilizar tokens determinísticos, sem texto livre variável. Ordem canônica mínima:

```text
1. OUTCOME_RULE
2. ANALYSIS_ID
3. REFERENCE_CANDLE_OPEN_TIME
4. REFERENCE_CANDLE_CLOSE_TIME
5. REFERENCE_CLOSE
6. FINAL_CANDLE_OPEN_TIME
7. FINAL_CANDLE_CLOSE_TIME
8. FINAL_CLOSE
9. HORIZON_CLOSED_CANDLES
10. REALIZED_RETURN_THRESHOLD
11. REALIZED_RETURN
12. REALIZED_STATE
```

A evidence do Outcome não substitui nem reescreve `Analysis.evidence`.

---

# 4. Contrato temporal

## 4.1 Instantes

Para uma `Analysis` persistida:

```text
Analysis.timestamp = T
```

A avaliação recebe ainda um corte temporal explícito:

```text
evaluation_as_of = E
```

`E` representa o instante lógico até o qual o módulo de avaliação está autorizado a observar Ground Truth.

Regras:

```text
T deve ser timezone-aware
E deve ser timezone-aware
E >= T
```

Não utilizar `datetime.now()` para decidir disponibilidade.

## 4.2 Candle de referência

O candle Ground Truth de referência é:

```text
reference =
último candle Ground Truth fechado
cujo close_time <= T
```

Se não existir candle de referência válido em ou antes de `T`, a avaliação retorna estado explícito de indisponibilidade e **não cria Outcome**.

## 4.3 Horizonte futuro

Seja:

```text
H = OutcomeConfig.horizon_closed_candles
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

## 4.4 Estados de disponibilidade

A orquestração deve representar explicitamente pelo menos:

```text
AVAILABLE
PENDING_HORIZON
UNAVAILABLE_REFERENCE
UNAVAILABLE_END_OF_DATASET
```

### `AVAILABLE`

Existe referência válida, existem exatamente `H` candles futuros fechados necessários e o candle final já está autorizado por `E`.

Somente neste estado o `OutcomeEvaluator` pode produzir e persistir `Outcome`.

### `PENDING_HORIZON`

Existe referência válida, porém menos de `H` candles futuros necessários estão disponíveis até `E`, e a fonte ainda não atingiu estado terminal para a sessão.

Resultado:

```text
nenhum Outcome
operação pode ser repetida posteriormente
```

### `UNAVAILABLE_REFERENCE`

Não existe candle Ground Truth fechado válido em ou antes de `T`.

Resultado:

```text
nenhum Outcome
nenhum resultado fictício
```

### `UNAVAILABLE_END_OF_DATASET`

A fonte chegou ao fim definitivo da sessão/dataset e existem menos de `H` candles fechados após a referência.

Resultado:

```text
nenhum Outcome
horizonte não é reduzido
```

Análises sem Outcome por indisponibilidade de referência, horizonte pendente ou fim de dataset não entram nas métricas de análises avaliadas.

## 4.5 Entradas temporais inválidas

Devem falhar explicitamente, sem persistência:

- `T` naive;
- `E` naive;
- `E < T`;
- Ground Truth com timestamps naive;
- janela fora da sessão da Analysis;
- referência com `close == 0`;
- dados Ground Truth estruturalmente inconsistentes.

---

# 5. Ground Truth boundary

## 5.1 Contrato dedicado

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

## 5.2 Fluxos permitidos e proibidos

Permitido:

```text
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

---

# 6. Fronteira contra future leakage

A distinção normativa é:

```text
ANALYSIS EM T
usa somente informação <= T
é persistida
é imutável

        ↓ tempo

OUTCOME EVALUATION EM E
pode observar somente o Ground Truth necessário
com close_time <= E

        ↓

OutcomeEvaluator
adiciona Outcome
nunca reescreve Analysis
```

Adicionar novos candles futuros, completar o horizonte ou avançar o replay pode alterar o estado de disponibilidade de `PENDING_HORIZON` para `AVAILABLE` e permitir a criação de Outcome.

Isso **não pode** alterar, recalcular ou substituir a Analysis histórica.

Um teste de regressão da FASE 6 deve continuar comprovando que adicionar futuro não altera `Analysis(T)`.

---

# 7. Estado realizado e política numérica

## 7.1 Fórmula canônica

Com:

```text
P0 = reference_close
P1 = final_close
```

O retorno realizado é:

```text
realized_return = (P1 - P0) / P0
```

`P0 == 0` é Ground Truth inválido para esta avaliação e deve falhar explicitamente.

## 7.2 Decimal

Para preservar a política numérica já estabelecida nas Market Features:

- `reference_close`, `final_close`, threshold e retorno usam `Decimal`;
- divisões usam `localcontext()` com precisão 28;
- arredondamento: `ROUND_HALF_EVEN`;
- não usar `float` para o cálculo do retorno realizado;
- não aplicar `quantize` silencioso.

## 7.3 Classificação do resultado

Seja:

```text
R = realized_return
D = realized_return_threshold
```

Regra exata:

```text
se R > D
→ UP

se R < -D
→ DOWN

caso contrário
→ SIDEWAYS
```

Logo:

```text
R == D  → SIDEWAYS
R == -D → SIDEWAYS
```

Com `D == 0`, somente retorno exatamente zero é `SIDEWAYS`.

---

# 8. Predicted state e `UNCERTAIN`

Para métricas da FASE 7:

```text
predicted_state = Analysis.market_state
```

Estados possíveis da previsão:

```text
UP
DOWN
SIDEWAYS
UNCERTAIN
```

Estados possíveis do resultado realizado:

```text
UP
DOWN
SIDEWAYS
```

`UNCERTAIN` significa que a Analysis se absteve de produzir uma classificação determinada.

Regras:

1. `UNCERTAIN` participa do total de análises avaliadas se existir Outcome correspondente;
2. `UNCERTAIN` nunca pode ser `realized_state`;
3. `UNCERTAIN` aparece como coluna de previsão da confusion matrix;
4. `UNCERTAIN` possui `uncertain_count` e `uncertain_frequency`;
5. coverage mede a fração de previsões diferentes de `UNCERTAIN`;
6. uma previsão `UNCERTAIN` nunca conta como acerto de accuracy;
7. `UNCERTAIN` não possui precision própria, porque não existe classe realizada equivalente;
8. uma previsão `UNCERTAIN` para um resultado realizado `C` conta como falso negativo de `C` e reduz `recall(C)`;
9. previsões `UNCERTAIN` não entram no denominador de `precision(UP)`, `precision(DOWN)` ou `precision(SIDEWAYS)`.

---

# 9. Conjunto avaliado

Uma unidade métrica válida é um par:

```text
(Analysis, Outcome)
```

com:

```text
Outcome.analysis_id == Analysis.analysis_id
```

Somente Outcomes persistidos e válidos entram nas métricas.

Defina:

```text
N = quantidade total de pares avaliados
```

Análises sem Outcome não entram em `N`.

---

# 10. Confusion matrix

A matriz possui orientação fixa:

```text
LINHAS   = realized_state
COLUNAS  = predicted_state
```

Ordem fixa das linhas:

```text
[UP, DOWN, SIDEWAYS]
```

Ordem fixa das colunas:

```text
[UP, DOWN, SIDEWAYS, UNCERTAIN]
```

Definição:

```text
M[r, p] = quantidade de pares
          com realized_state == r
          e predicted_state == p
```

A soma das 12 células deve ser exatamente `N`.

---

# 11. Accuracy

Defina:

```text
correct =
M[UP, UP]
+ M[DOWN, DOWN]
+ M[SIDEWAYS, SIDEWAYS]
```

Então:

```text
accuracy = correct / N
```

Previsões `UNCERTAIN` estão no denominador `N`, mas nunca no numerador.

Se `N == 0`:

```text
accuracy = None
```

---

# 12. Precision por classe

Precision é definida somente para as três classes realizáveis:

```text
C ∈ {UP, DOWN, SIDEWAYS}
```

```text
precision(C) =
M[C, C]
/
sum(M[r, C] para r em {UP, DOWN, SIDEWAYS})
```

Se nenhuma previsão da classe `C` existir:

```text
precision(C) = None
```

Não existe `precision(UNCERTAIN)` no MVP.

---

# 13. Recall por classe

Para:

```text
C ∈ {UP, DOWN, SIDEWAYS}
```

```text
recall(C) =
M[C, C]
/
sum(M[C, p] para p em {UP, DOWN, SIDEWAYS, UNCERTAIN})
```

Assim, uma previsão `UNCERTAIN` quando o realizado foi `C` reduz o recall de `C`.

Se nenhum resultado realizado da classe `C` existir:

```text
recall(C) = None
```

---

# 14. Coverage e `UNCERTAIN`

```text
uncertain_count =
sum(M[r, UNCERTAIN] para r em {UP, DOWN, SIDEWAYS})
```

```text
non_uncertain_count = N - uncertain_count
```

```text
coverage = non_uncertain_count / N
```

```text
uncertain_frequency = uncertain_count / N
```

Invariante quando `N > 0`:

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

# 15. Política numérica das métricas

Contagens são inteiros.

Razões derivadas devem ser calculadas deterministicamente com `Decimal` em contexto local de precisão 28 e `ROUND_HALF_EVEN`.

Quando uma razão possuir denominador zero, retornar `None`, nunca inventar `0.0`.

Nenhuma métrica pode alterar Analysis, Outcome ou confidence persistidos.

---

# 16. Confidence calibration no MVP

## 16.1 Semântica

`Analysis.confidence` continua sendo a confiança operacional do classificador rule-based definida na FASE 6.

Ela **não é probabilidade estatística**.

A FASE 7 não recalibra nem reescreve confidence. Ela produz somente um diagnóstico empírico da relação entre confidence registrada e acerto posteriormente observado.

## 16.2 Conjunto utilizado

Entram no diagnóstico somente pares avaliados cuja previsão seja:

```text
UP
DOWN
SIDEWAYS
```

Pares com `Analysis.market_state == UNCERTAIN` são excluídos da calibração porque representam abstention, não uma previsão determinada.

Defina:

```text
Nc = quantidade de pares não-UNCERTAIN avaliados
```

## 16.3 Conversão numérica

Para agregação determinística:

```text
confidence_decimal = Decimal(str(Analysis.confidence))
```

A confidence deve continuar válida em `[0, 1]`.

## 16.4 Bins canônicos

O MVP utiliza cinco bins fixos e explicitamente documentados:

```text
B1 = [0.0, 0.2)
B2 = [0.2, 0.4)
B3 = [0.4, 0.6)
B4 = [0.6, 0.8)
B5 = [0.8, 1.0]
```

`1.0` pertence ao último bin.

Os bins não são defaults escondidos; são parte normativa do contrato MVP.

## 16.5 Métricas por bin

Para cada bin `b`:

```text
n_b = quantidade de pares no bin
```

Se `n_b > 0`:

```text
mean_confidence_b = soma(confidence_decimal) / n_b

observed_accuracy_b =
quantidade de previsões corretas no bin / n_b

absolute_gap_b =
abs(mean_confidence_b - observed_accuracy_b)
```

Se `n_b == 0`:

```text
mean_confidence_b = None
observed_accuracy_b = None
absolute_gap_b = None
```

## 16.6 Diagnóstico agregado

Quando `Nc > 0`:

```text
weighted_alignment_gap =
sum(
    (n_b / Nc) * absolute_gap_b
    para bins não vazios
)
```

Quando `Nc == 0`:

```text
weighted_alignment_gap = None
```

Esse valor é apenas um **diagnóstico de alinhamento operacional**, não ECE probabilístico, não Brier score e não prova de calibração estatística.

O relatório de confidence calibration do MVP deve expor:

- os cinco bins na ordem canônica;
- `n_b`;
- `mean_confidence_b`;
- `observed_accuracy_b`;
- `absolute_gap_b`;
- `weighted_alignment_gap`.

---

# 17. Persistência de Outcome

## 17.1 Tabela conceitual

A FASE 7 implementará posteriormente uma tabela:

```text
outcomes
```

Esta missão de governança **não cria migration nem tabela**.

## 17.2 Campos mínimos

A persistência deve representar, sem perda semântica, os campos canônicos de `Outcome`:

```text
analysis_id

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

## 17.3 Constraints mínimas

- `analysis_id` como primary key;
- `analysis_id` também foreign key para `analyses.analysis_id`;
- FK com política que preserve auditoria; não apagar Analysis silenciosamente através do Outcome;
- timestamps obrigatórios e timezone-aware na borda de domínio;
- `horizon_closed_candles >= 1`;
- `realized_return_threshold >= 0`;
- `realized_state` limitado a `UP`, `DOWN`, `SIDEWAYS`;
- `reference_close != 0`;
- `final_candle_close_time > reference_candle_close_time`;
- evidence persistida em representação ordenada com round-trip sem perda;
- valores Decimal persistidos como numéricos exatos, não `float`.

Validações que dependem da `Analysis`, como `reference_candle_close_time <= Analysis.timestamp`, devem ser garantidas pela camada de domínio/orquestração e testadas também na integração.

## 17.4 Imutabilidade

Não existe UPDATE semântico de Outcome no MVP.

Após persistido, qualquer tentativa de alterar horizonte, threshold, preços de referência/final, retorno, realized state, timestamps ou evidence para a mesma identidade deve produzir conflito explícito.

## 17.5 Métricas não são tabela no MVP

Accuracy, precision, recall, confusion matrix, coverage e confidence calibration são agregados derivados de `Analysis + Outcome`.

A FASE 7 não precisa criar tabela de métricas persistidas. Persistir agregados fica fora do MVP enquanto não existir decisão específica.

---

# 18. Identidade, idempotência e reavaliação

Cardinalidade canônica do MVP:

```text
Analysis 1 → 0..1 Outcome
```

Identidade:

```text
Outcome identity = analysis_id
```

Regras:

```text
mesmo analysis_id + mesmos dados completos de Outcome
→ operação idempotente permitida

mesmo analysis_id + qualquer dado de Outcome diferente
→ conflito explícito
```

Erro conceitual:

```text
OutcomeConflictError
```

### Reavaliação

Enquanto não existe Outcome:

- `PENDING_HORIZON` pode ser reavaliado posteriormente;
- quando o horizonte fica disponível, um único Outcome pode ser criado.

Depois de persistido:

- repetir a avaliação com a mesma configuração e mesmo Ground Truth deve reproduzir exatamente o mesmo Outcome e ser idempotente;
- configuração diferente para a mesma Analysis não pode sobrescrever o Outcome existente;
- Ground Truth divergente para a mesma identidade deve produzir conflito, nunca atualização.

Múltiplos horizontes ou múltiplas configurações simultâneas por Analysis são `FUTURE` e exigem nova decisão/escopo.

---

# 19. `OutcomeEvaluator`

`OutcomeEvaluator` é componente de domínio puro.

Responsabilidades:

1. receber uma `Analysis` já persistida/imutável;
2. receber candle de referência Ground Truth válido;
3. receber candle final Ground Truth válido;
4. receber `OutcomeConfig`;
5. validar invariantes de domínio;
6. calcular `realized_return`;
7. classificar `RealizedState`;
8. produzir `Outcome` determinístico.

Não acessa:

- PostgreSQL;
- SQLAlchemy;
- FastAPI;
- filesystem;
- relógio real;
- `StorageProvider`;
- `ReplaySource` diretamente;
- provider de Ground Truth diretamente;
- frontend;
- Dashboard.

Propriedade obrigatória:

```text
mesma Analysis
+ mesma referência
+ mesmo candle final
+ mesma configuração
=
mesmo Outcome
```

---

# 20. Orquestração

A camada conceitual de aplicação/domínio responsável pela fase é denominada:

```text
OutcomeEvaluationService
```

Responsabilidades:

1. receber `analysis_id`, `evaluation_as_of` e `OutcomeConfig`;
2. carregar `Analysis` pelo `StorageProvider`;
3. rejeitar Analysis inexistente;
4. validar timestamps e configuração;
5. consultar `GroundTruthProvider.get_evaluation_window(...)`;
6. interpretar `AVAILABLE`, `PENDING_HORIZON`, `UNAVAILABLE_REFERENCE` ou `UNAVAILABLE_END_OF_DATASET`;
7. chamar `OutcomeEvaluator` somente quando `AVAILABLE`;
8. persistir Outcome imutável;
9. retornar Outcome/status de disponibilidade sem modificar Analysis.

A orquestração pode depender de `StorageProvider` e `GroundTruthProvider`.

O `OutcomeEvaluator` não depende desses providers.

---

# 21. Extensões futuras mínimas de `StorageProvider`

Quando a implementação da FASE 7 for autorizada, o contrato de storage poderá ser estendido somente com o mínimo necessário:

```text
save_outcome(outcome: Outcome) -> None

get_outcome(analysis_id: str) -> Outcome | None

list_outcomes() -> tuple[Outcome, ...]
```

Mais o conflito explícito equivalente:

```text
OutcomeConflictError
```

Para métricas, `list_outcomes()` combinado com `get_analysis(outcome.analysis_id)` é suficiente no MVP. Consultas agregadas/otimizadas podem ser introduzidas somente se necessidade concreta for demonstrada, sem alterar a semântica.

Ground Truth **não** deve ser incorporado ao `StorageProvider`; ele possui contrato próprio de avaliação.

---

# 22. Contrato das métricas

A camada de métricas deve ser pura e receber pares `Analysis + Outcome` já carregados.

Ela não deve:

- consultar Ground Truth;
- recalcular Outcome;
- alterar Analysis;
- alterar Outcome;
- consultar relógio;
- depender de PostgreSQL;
- depender de ReplaySource.

Resultado conceitual mínimo:

```text
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

A ordem das classes e regras de denominador deste documento são normativas.

---

# 23. Critérios de aceite da FASE 7

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
15. `Analysis` permanece byte/semanticamente inalterada antes e depois da avaliação;
16. `AnalysisEngine` e `AnalysisLabService` permanecem sem acesso a Ground Truth/OutcomeEvaluator;
17. adicionar futuro continua sem alterar `Analysis(T)`;
18. `OutcomeEvaluator` é determinístico para mesma entrada/configuração;
19. Outcome persistido realiza round-trip sem perda de Decimal, timestamps ou evidence;
20. Outcome persistido é imutável;
21. mesma identidade + mesmos dados é idempotente;
22. mesma identidade + dados diferentes produz `OutcomeConflictError`;
23. confusion matrix usa linhas `[UP, DOWN, SIDEWAYS]` e colunas `[UP, DOWN, SIDEWAYS, UNCERTAIN]`;
24. accuracy usa todas as análises avaliadas no denominador e trata `UNCERTAIN` como não acerto;
25. precision por `UP`, `DOWN`, `SIDEWAYS` segue o denominador de previsões da respectiva classe e retorna `None` com denominador zero;
26. recall por `UP`, `DOWN`, `SIDEWAYS` inclui previsões `UNCERTAIN` como falso negativo e retorna `None` com denominador zero;
27. coverage é a fração de previsões não-`UNCERTAIN`;
28. `uncertain_count` e `uncertain_frequency` obedecem às fórmulas canônicas;
29. para `N == 0`, accuracy/coverage/uncertain_frequency são `None` e contagens/matriz permanecem zero;
30. confidence calibration exclui `UNCERTAIN`, utiliza os cinco bins canônicos e produz estatísticas por bin determinísticas;
31. bin vazio retorna métricas de bin `None` sem contaminar o agregado;
32. `weighted_alignment_gap` usa somente previsões determinadas e retorna `None` quando `Nc == 0`;
33. nenhuma métrica, Outcome ou execução de avaliação altera retrospectivamente `Analysis.confidence` ou qualquer outro campo da Analysis;
34. nenhuma funcionalidade da FASE 8/Dashboard é introduzida;
35. nenhuma integração financeira, corretora, ML/RL, novos indicadores ou escopo pós-v1 é introduzido.

Cada critério deve possuir teste automatizado ou evidência automatizada equivalente no fechamento formal.

---

# 24. Test plan obrigatório

## 24.1 Unidade — `OutcomeConfig`

Cobrir no mínimo:

```text
horizon >= 1
horizon inválido
threshold zero
threshold positivo
threshold negativo
threshold NaN/infinito
```

## 24.2 Unidade — `OutcomeEvaluator`

Cobrir:

```text
UP acima do threshold
DOWN abaixo de -threshold
SIDEWAYS dentro da faixa
igualdade em +threshold
igualdade em -threshold
reference_close zero
sessão/contexto inconsistente
timestamps inválidos
mesma entrada → mesmo Outcome
evidence determinística
```

## 24.3 Orquestração/horizonte

Com provider fake/determinístico:

```text
última referência fechada <= T
H-ésimo candle futuro
horizonte disponível
PENDING_HORIZON
UNAVAILABLE_REFERENCE
UNAVAILABLE_END_OF_DATASET
não sintetizar gaps
não retornar candle futuro além de evaluation_as_of
```

## 24.4 Arquitetura / Ground Truth

Teste arquitetural deve provar que:

- `AnalysisEngine` não importa `GroundTruthProvider`, ReplaySource ou OutcomeEvaluator;
- `AnalysisLabService` não consulta Ground Truth;
- pipeline visual continua isolado de Ground Truth;
- Outcome Evaluation acessa Ground Truth apenas pelo contrato autorizado.

## 24.5 Regressão anti-future-leakage

Reexecutar os testes da FASE 6 que comprovam:

```text
future candle
future snapshot
evolução futura de candle conhecido
```

não alteram `Analysis(T)`.

Adicionar teste integrado em que o avanço do futuro muda somente:

```text
PENDING_HORIZON → AVAILABLE/Outcome
```

sem modificar a Analysis original.

## 24.6 Métricas

Testes unitários devem cobrir:

- matriz de confusão completa;
- ordem fixa de linhas/colunas;
- accuracy;
- precision por cada classe;
- precision com denominador zero;
- recall por cada classe;
- recall reduzido por `UNCERTAIN`;
- recall com denominador zero;
- coverage;
- uncertain count;
- uncertain frequency;
- `N == 0`;
- invariantes de soma da matriz;
- `coverage + uncertain_frequency == 1` quando `N > 0`.

## 24.7 Confidence calibration

Cobrir:

- cada um dos cinco bins;
- limites `0.0`, `0.2`, `0.4`, `0.6`, `0.8`, `1.0`;
- exclusão de `UNCERTAIN`;
- média de confidence;
- observed accuracy;
- absolute gap;
- weighted alignment gap;
- bins vazios;
- `Nc == 0`.

## 24.8 Persistência PostgreSQL futura

Quando autorizada a implementação:

- migration cria somente estruturas da FASE 7 necessárias;
- round-trip Outcome;
- Decimal preservado;
- timestamps preservados;
- FK obrigatória para Analysis;
- uma linha por `analysis_id`;
- mesma gravação idempotente;
- conflito explícito;
- imutabilidade;
- migration upgrade/downgrade/re-upgrade.

## 24.9 Regressão completa

Executar novamente os testes relevantes das FASES 1–6, especialmente:

- Replay gate temporal;
- isolamento de Ground Truth da visão;
- Temporal Memory;
- point-in-time `get_candles_as_of`;
- FeatureEngine;
- AnalysisEngine;
- AnalysisLabService;
- persistência imutável de Analysis;
- CI completo, frontend build e Docker Compose conforme pipeline oficial.

---

# 25. Resolução dos blockers do Phase Start

| Blocker | Resolução canônica |
|---|---|
| BLOCKER-01 — Outcome indefinido | Seções 3 e 17 definem modelo, campos, invariantes e persistência. |
| BLOCKER-02 — horizonte indefinido | Seção 4 define referência, H candles futuros e disponibilidade. |
| BLOCKER-03 — conversão futura para classe | Seção 7 define retorno e UP/DOWN/SIDEWAYS com limites exatos. |
| BLOCKER-04 — Ground Truth contract | Seção 5 define `GroundTruthProvider` exclusivo da avaliação. |
| BLOCKER-05 — fronteira temporal | Seções 4 e 6 definem `T`, `E`, horizonte e proibição de alteração histórica. |
| BLOCKER-06 — UNCERTAIN nas métricas | Seção 8 define abstention e efeito em cada família métrica. |
| BLOCKER-07 — fórmulas das métricas | Seções 10–15 definem matriz, denominadores e zero denominator. |
| BLOCKER-08 — confidence calibration | Seção 16 define diagnóstico operacional, bins e fórmula. |
| BLOCKER-09 — persistência | Seção 17 define tabela conceitual, campos e constraints. |
| BLOCKER-10 — identidade/idempotência | Seção 18 define `analysis_id`, 1:0..1, idempotência e conflito. |
| BLOCKER-11 — orquestração/storage | Seções 20–22 definem service, providers e extensões mínimas futuras. |
| BLOCKER-12 — aceite/testes | Seções 23 e 24 definem critérios verificáveis e test plan. |

Os blockers de especificação são considerados resolvidos **documentalmente** quando esta especificação estiver integrada ao `main` com CI verde. Isso não equivale a `PHASE_START = READY`; o Phase Start deve ser reexecutado.

---

# 26. Fora do escopo da FASE 7

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
- múltiplos Outcomes/horizontes/configurações por Analysis;
- tabela persistente de métricas agregadas;
- fontes externas além do replay controlado do v1.

---

# 27. Sequência permitida após novo PHASE START

Somente depois de `chartvision-phase-start = READY`, a implementação poderá ser dividida em incrementos pequenos.

A primeira missão técnica deve permanecer limitada aos contratos puros de domínio necessários ao Outcome Evaluation, sem antecipar persistence, API, frontend ou Dashboard salvo autorização específica do Phase Brief.

Este documento não cria essa autorização por si só.

---

# 28. Definition of Done específica

A FASE 7 exigirá, no fechamento:

```text
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
Outcome imutável/idempotente comprovado
+
accuracy/precision/recall/matriz comprovados
+
coverage/UNCERTAIN comprovados
+
confidence calibration diagnóstica comprovada
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

# 29. Resumo normativo

```text
ANALYSIS
Analysis.timestamp = T
Analysis imutável

        ↓

OUTCOME CONFIG
H >= 1 candles fechados
threshold Decimal >= 0

        ↓

GROUND TRUTH PROVIDER
reference = último fechado <= T
+ no máximo H futuros fechados <= evaluation_as_of

        ↓

HORIZON GATE
sem H completo → nenhum Outcome
fim do dataset → nenhum horizonte reduzido

        ↓

REALIZED RETURN
(final_close - reference_close) / reference_close
Decimal precision 28 / ROUND_HALF_EVEN

        ↓

REALIZED STATE
R > D   → UP
R < -D  → DOWN
senão   → SIDEWAYS

        ↓

OUTCOME
identity = analysis_id
imutável
1 Analysis → 0..1 Outcome

        ↓

METRICS
rows realized: UP/DOWN/SIDEWAYS
cols predicted: UP/DOWN/SIDEWAYS/UNCERTAIN
accuracy / precision / recall
coverage / uncertain
confidence alignment diagnostic

        ↓

FASE 8
continua bloqueada até PHASE_CLOSE = PASS
```
