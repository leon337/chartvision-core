# ChartVision Core — Analysis Lab MVP

## Escopo da FASE 6

Este documento define o contrato funcional canônico da **FASE 6 — ANALYSIS LAB MVP**.

A FASE 6 tem como responsabilidade classificar deterministicamente o estado atual conhecido do gráfico em exatamente um dos quatro estados:

```text
UP
DOWN
SIDEWAYS
UNCERTAIN
```

A classificação deve utilizar exclusivamente informação disponível até o instante `as_of`.

A FASE 6 não realiza previsão financeira operacional, avaliação posterior de resultado ou execução de ordens.

---

# 1. Objetivo

Transformar características estruturais já disponibilizadas pela FASE 5 em uma classificação experimental, reproduzível e auditável do estado conhecido do gráfico.

Fluxo canônico:

```text
Temporal Memory
        ↓
get_candles_as_of(session_id, as_of)
        ↓
candles conhecidos no corte temporal
        ↓
FeatureEngine
        ↓
features necessárias à análise
        ↓
AnalysisEngine
        ↓
AnalysisDecision
        ↓
Analysis persistida
```

O `AnalysisEngine` não acessa banco, replay, Ground Truth ou informação futura.

---

# 2. Fronteira temporal obrigatória

Toda análise deve começar pela primitive point-in-time já estabelecida:

```text
StorageProvider.get_candles_as_of(session_id, as_of)
```

Regras:

1. `as_of` deve ser timezone-aware;
2. somente informação conhecida em `as_of` pode participar;
3. snapshots posteriores são proibidos;
4. estado canônico posterior de um candle não pode reconstruir retrospectivamente o passado;
5. candles futuros não participam;
6. `ReplaySource` não pode ser consultado pelo módulo de análise;
7. Ground Truth não pode participar;
8. OutcomeEvaluator não pode participar;
9. adicionar dados depois de `as_of` não pode alterar uma análise histórica para o mesmo corte.

Fluxo proibido:

```text
AnalysisEngine
    ↓
ReplaySource / Ground Truth / futuro
```

---

# 3. Separação de responsabilidades

## 3.1 Orquestração da análise

A FASE 6 deve possuir uma camada de orquestração point-in-time, conceitualmente denominada neste documento:

```text
AnalysisLabService
```

O nome concreto pode permanecer equivalente se a implementação preservar o contrato.

Responsabilidades:

1. receber `session_id`, `as_of` e configuração;
2. validar `as_of`;
3. executar `get_candles_as_of(session_id, as_of)`;
4. calcular as features necessárias usando `FeatureEngine`;
5. calcular a qualidade dos dados utilizados;
6. entregar somente esses resultados ao `AnalysisEngine`;
7. criar o registro `Analysis`;
8. persistir a análise imutável.

Essa camada pode depender de `StorageProvider`.

Ela não pode depender de `ReplaySource`, Ground Truth ou OutcomeEvaluator.

---

## 3.2 FeatureEngine

`FeatureEngine` continua responsável exclusivamente pelos cálculos da FASE 5.

A FASE 6 não deve duplicar:

- HH;
- HL;
- LH;
- LL;
- tendência estrutural;
- lateralização;
- ou outras fórmulas da FASE 5.

---

## 3.3 AnalysisEngine

`AnalysisEngine` é um componente de domínio puro.

Não acessa:

- PostgreSQL;
- SQLAlchemy;
- psycopg;
- FastAPI;
- filesystem;
- relógio real;
- `StorageProvider`;
- `ReplaySource`;
- Ground Truth;
- OutcomeEvaluator.

Ele recebe resultados já calculados e retorna uma decisão determinística.

---

# 4. Features utilizadas pela classificação

O classificador MVP utiliza somente:

```text
BasicTrend
basic_lateralization
```

Portanto, as duas entradas funcionais de classificação são:

```text
basic_trend:
    RISING_STRUCTURE
    FALLING_STRUCTURE
    MIXED_STRUCTURE
    None

basic_lateralization:
    True
    False
    None
```

A qualidade dos dados é uma entrada adicional de controle, não uma nova Market Feature.

As demais características da FASE 5 não participam diretamente da decisão da FASE 6 v1:

- direção do candle;
- amplitude;
- retorno;
- volatilidade.

HH/HL/LH/LL participam indiretamente porque fazem parte da definição de `BasicTrend`.

Não adicionar pesos, indicadores extras ou combinações heurísticas dessas features durante a FASE 6 sem nova alteração formal desta especificação.

---

# 5. Por que somente tendência e lateralização

O objetivo da FASE 6 é produzir o menor classificador determinístico capaz de representar os quatro estados definidos no roadmap.

Mapeamento conceitual:

```text
estrutura ascendente
        ↓
UP

estrutura descendente
        ↓
DOWN

estrutura mista + faixa lateral válida
        ↓
SIDEWAYS

ausência de evidência suficiente ou consistente
        ↓
UNCERTAIN
```

Isso evita introduzir pesos arbitrários ou lógica estatística não aprovada.

---

# 6. Configuração explícita

A análise não possui parâmetros numéricos implícitos.

A configuração deve fornecer:

```text
trend_pairs: int
lateralization_window_candles: int
lateralization_max_range_ratio: Decimal
minimum_data_quality: float
```

Validações:

```text
trend_pairs >= 1

lateralization_window_candles >= 3

lateralization_max_range_ratio >= 0

0.0 <= minimum_data_quality <= 1.0
```

Parâmetro inválido gera `ValueError`.

Nenhum default silencioso deve existir no domínio.

---

# 7. Política de candles

A classificação da FASE 6 utiliza somente candles fechados para tendência e lateralização.

Um candle atualmente aberto pode existir dentro do conjunto retornado por:

```text
get_candles_as_of(...)
```

mas não participa diretamente da classificação.

Consequência:

```text
candle aberto
    ≠
nova classificação estrutural baseada nele
```

Isso mantém alinhamento com a política estrutural definida na FASE 5.

---

# 8. Histórico mínimo

O número mínimo de candles fechados necessário para uma análise determinada é:

```text
required_closed_candles =
max(
    trend_pairs + 1,
    lateralization_window_candles
)
```

Se existirem menos candles fechados que esse valor:

```text
MarketState.UNCERTAIN
```

A análise não inventa candles, não preenche gaps e não reduz automaticamente as janelas configuradas.

---

# 9. Qualidade dos dados

## 9.1 Fonte

A qualidade utilizada pela FASE 6 deriva exclusivamente dos candles reconstruídos efetivamente utilizados na janela da decisão.

No v1 é utilizado:

```text
Candle.vision_confidence
```

`source_confidence` não participa do Analysis Lab MVP.

---

## 9.2 Cálculo

Selecionar os últimos:

```text
required_closed_candles
```

candles fechados elegíveis.

Se todos possuem `vision_confidence` válido:

```text
data_quality =
min(vision_confidence dos candles utilizados)
```

A escolha do mínimo é deliberadamente conservadora: a qualidade da análise não deve esconder um candle estruturalmente importante com baixa confiança.

Valores válidos:

```text
0.0 <= vision_confidence <= 1.0
```

Valor fora desse intervalo é entrada inválida.

Se algum candle necessário possuir:

```text
vision_confidence = None
```

então:

```text
data_quality = None
```

Dados ausentes não devem ser inventados.

---

# 10. Gate de qualidade

Se:

```text
data_quality is None
```

ou:

```text
data_quality < minimum_data_quality
```

o resultado obrigatório é:

```text
UNCERTAIN
```

Nenhuma regra direcional ou lateral pode sobrescrever o gate de qualidade.

Se:

```text
data_quality == minimum_data_quality
```

a análise pode prosseguir normalmente.

---

# 11. Regras canônicas de classificação

A avaliação segue esta ordem exata.

## Regra 1 — histórico insuficiente

```text
se histórico mínimo não existe
→ UNCERTAIN
```

## Regra 2 — qualidade insuficiente

```text
se data_quality é None
→ UNCERTAIN

se data_quality < minimum_data_quality
→ UNCERTAIN
```

## Regra 3 — lateralização indisponível

```text
se basic_lateralization is None
→ UNCERTAIN
```

Não é permitido declarar `UP` ou `DOWN` sem conseguir avaliar a regra de lateralização configurada.

## Regra 4 — lateralização confirmada

```text
se basic_lateralization is True
→ SIDEWAYS
```

Esta regra possui precedência sobre tendência calculada em outra janela.

## Regra 5 — estrutura ascendente

```text
se:
basic_lateralization is False
e
basic_trend == RISING_STRUCTURE

→ UP
```

## Regra 6 — estrutura descendente

```text
se:
basic_lateralization is False
e
basic_trend == FALLING_STRUCTURE

→ DOWN
```

## Regra 7 — restante dos casos

```text
→ UNCERTAIN
```

Inclui explicitamente:

```text
MIXED_STRUCTURE + lateralization=False
trend=None
combinação não reconhecida
evidência estrutural insuficiente
```

---

# 12. Tabela de decisão

| Qualidade válida | Lateralização | Tendência | Estado |
|---|---|---|---|
| não | qualquer | qualquer | `UNCERTAIN` |
| sim | `None` | qualquer | `UNCERTAIN` |
| sim | `True` | qualquer | `SIDEWAYS` |
| sim | `False` | `RISING_STRUCTURE` | `UP` |
| sim | `False` | `FALLING_STRUCTURE` | `DOWN` |
| sim | `False` | `MIXED_STRUCTURE` | `UNCERTAIN` |
| sim | `False` | `None` | `UNCERTAIN` |

Essa tabela é normativa.

---

# 13. Precedência canônica

A precedência é:

```text
HISTÓRICO
    ↓
QUALIDADE
    ↓
SIDEWAYS
    ↓
UP / DOWN
    ↓
UNCERTAIN
```

Formalmente:

```text
INSUFFICIENT
>
LOW_QUALITY
>
SIDEWAYS
>
DIRECTIONAL
>
UNCERTAIN_FALLBACK
```

Isso significa que uma estrutura curta ascendente não pode produzir `UP` quando a janela configurada de lateralização classifica o mercado como lateral.

---

# 14. Contrato do AnalysisEngine

Contrato conceitual mínimo:

```text
AnalysisEngine.classify(
    basic_trend,
    basic_lateralization,
    data_quality,
    minimum_data_quality,
) -> AnalysisDecision
```

`AnalysisEngine` não recebe:

```text
session_id
as_of
StorageProvider
Candle
ReplaySource
Ground Truth
Outcome
```

Metadados temporais e persistência pertencem à orquestração.

---

# 15. AnalysisDecision

O resultado puro da classificação deve representar:

```text
market_state
confidence
data_quality
evidence
```

`AnalysisDecision` é conceitualmente um value object imutável.

A decisão não contém identidade de persistência.

Isso permite:

```text
mesmas features
+ mesma qualidade
+ mesma configuração
=
mesmo AnalysisDecision
```

---

# 16. MarketState

O enum existente é ratificado para a FASE 6:

```text
MarketState.UP
MarketState.DOWN
MarketState.SIDEWAYS
MarketState.UNCERTAIN
```

Não renomear para `AnalysisState` durante a FASE 6 sem necessidade arquitetural comprovada.

---

# 17. Semântica de confidence

`confidence` representa a confiança operacional da análise produzida pelo classificador rule-based.

Não é probabilidade estatística.

No MVP:

```text
se market_state != UNCERTAIN:
    confidence = data_quality

se market_state == UNCERTAIN:
    confidence = 0.0
```

Como qualquer estado determinado já satisfaz uma regra estrutural binária, a limitação principal da confiança é a qualidade dos dados de entrada.

Não criar pesos artificiais para elevar ou reduzir `confidence`.

A calibração posterior de confiança pertence à FASE 7.

---

# 18. Semântica de data_quality

`data_quality` representa a qualidade mínima dos candles utilizados na decisão.

Contrato canônico para o modelo da FASE 6:

```text
data_quality: float | None
```

Isso substitui semanticamente o placeholder inicial `float` quando a implementação da FASE 6 for realizada.

Motivo:

```text
ausência de qualidade
≠
qualidade zero observada
```

Dados ausentes não devem ser inventados.

---

# 19. Evidence

`evidence` permanece:

```text
tuple[str, ...]
```

e deve conter tokens auditáveis e determinísticos.

Não utilizar texto livre variável.

Ordem canônica:

```text
1. regra que produziu o estado
2. BasicTrend
3. basic_lateralization
4. data_quality
5. configuração relevante
6. motivo adicional de UNCERTAIN, quando aplicável
```

Exemplo:

```text
STATE_RULE=RISING_STRUCTURE
BASIC_TREND=RISING_STRUCTURE
BASIC_LATERALIZATION=FALSE
DATA_QUALITY=0.91
TREND_PAIRS=3
LATERALIZATION_WINDOW_CANDLES=5
LATERALIZATION_MAX_RANGE_RATIO=0.02
MINIMUM_DATA_QUALITY=0.80
```

Exemplo de incerteza:

```text
STATE_RULE=INSUFFICIENT_HISTORY
BASIC_TREND=NONE
BASIC_LATERALIZATION=NONE
DATA_QUALITY=NONE
```

`evidence` serve para auditoria.

Não deve conter previsão futura ou resultado posteriormente observado.

---

# 20. Analysis persistida

A classificação deve ser registrada na FASE 6 para permitir auditoria e futura avaliação pela FASE 7.

O modelo conceitual permanece:

```text
Analysis
```

Campos:

```text
analysis_id
session_id
timestamp
market_state
confidence
data_quality
evidence
```

Regra temporal obrigatória:

```text
Analysis.timestamp == as_of
```

O timestamp representa o instante lógico da análise, não o instante real em que o processo Python executou.

---

# 21. Imutabilidade da análise

Após persistida, uma `Analysis` é imutável.

É proibido posteriormente alterar:

```text
market_state
confidence
data_quality
evidence
timestamp
session_id
```

para fazer a análise concordar com eventos futuros.

A FASE 7 adicionará avaliação posterior sem modificar o registro original.

---

# 22. Identidade e idempotência

`analysis_id` é a identidade persistente do registro.

O algoritmo de geração do ID não participa da lógica do `AnalysisEngine`.

A regra mínima da FASE 6 é:

```text
mesmo analysis_id + mesmos dados
→ operação idempotente permitida

mesmo analysis_id + dados diferentes
→ conflito explícito
```

Não criar deduplicação implícita por horário ou por estado nesta fase.

---

# 23. Persistência mínima da FASE 6

A FASE 6 deve estender `StorageProvider` somente com o mínimo necessário:

```text
save_analysis(analysis: Analysis) -> None

get_analysis(analysis_id: str) -> Analysis | None
```

Também deve existir conflito explícito equivalente aos contratos anteriores:

```text
AnalysisConflictError
```

Consultas específicas necessárias ao OutcomeEvaluator podem ser adicionadas somente na FASE 7.

---

# 24. Determinismo

A decisão deve obedecer:

```text
mesma entrada
+ mesma configuração
=
mesma decisão
```

É proibida dependência de:

```text
datetime.now()
random
estado global mutável
ordem incidental de banco
dados posteriores
execuções anteriores
ReplaySource
Ground Truth
OutcomeEvaluator
```

`analysis_id` não faz parte dessa propriedade porque pertence à identidade persistente, não à decisão de domínio.

---

# 25. Future leakage

O teste principal da FASE 6 deve comprovar:

```text
1. persistir histórico conhecido até T

2. executar:
   analyze(session_id, as_of=T, config)
   → R1

3. adicionar depois:
   - candles futuros
   - snapshots futuros
   - evolução posterior de candle existente

4. executar novamente:
   analyze(session_id, as_of=T, config)
   → R2

5. comparar decisões

ASSERT:
R1.market_state == R2.market_state
R1.confidence == R2.confidence
R1.data_quality == R2.data_quality
R1.evidence == R2.evidence
```

Esse teste é obrigatório.

Não basta testar somente:

```text
open_time > T
```

É necessário provar também que uma atualização posterior do estado canônico de candle já existente não contamina a análise histórica.

---

# 26. Estados de insuficiência e UNCERTAIN

`INSUFFICIENT_DATA` continua sendo um conceito sistêmico.

Na saída normal do `AnalysisEngine`, insuficiência válida de histórico é convertida para:

```text
MarketState.UNCERTAIN
```

com evidence:

```text
STATE_RULE=INSUFFICIENT_HISTORY
```

Portanto:

```text
histórico insuficiente
→ análise válida
→ UNCERTAIN
```

Não é uma exceção.

Erros de contrato, por outro lado, continuam sendo exceções.

Exemplos:

```text
as_of naive
configuração inválida
confidence fora de [0, 1]
session inconsistente
```

---

# 27. Critérios de aceite

A FASE 6 somente poderá ser considerada concluída quando houver evidência automatizada de todos os itens:

1. `UP` produzido para estrutura ascendente válida;
2. `DOWN` produzido para estrutura descendente válida;
3. `SIDEWAYS` produzido quando lateralização é verdadeira;
4. `UNCERTAIN` produzido para estrutura mista não lateral;
5. `UNCERTAIN` produzido para histórico insuficiente;
6. `UNCERTAIN` produzido para baixa qualidade;
7. igualdade no threshold de qualidade é aceita;
8. SIDEWAYS possui precedência sobre tendência direcional calculada em janela diferente;
9. mesmo input + configuração gera mesma decisão;
10. candle aberto não altera indevidamente a classificação estrutural;
11. nenhum dado posterior a `as_of` participa;
12. evolução futura de candle já conhecido não altera análise histórica;
13. AnalysisEngine permanece domínio puro;
14. análise persistida permanece imutável;
15. nenhuma funcionalidade da FASE 7 ou 8 é introduzida.

---

# 28. Testes obrigatórios

## Unidade — AnalysisEngine

No mínimo:

```text
test_classifies_up
test_classifies_down
test_classifies_sideways
test_mixed_non_lateral_is_uncertain
test_missing_trend_is_uncertain
test_missing_lateralization_is_uncertain
test_low_data_quality_is_uncertain
test_missing_data_quality_is_uncertain
test_quality_equal_threshold_is_allowed
test_sideways_precedes_directional_state
test_same_input_produces_same_decision
```

## Orquestração

```text
test_rejects_naive_as_of
test_uses_point_in_time_candles
test_excludes_open_candle_from_structural_window
test_builds_deterministic_evidence
```

## Anti-future-leakage

```text
test_future_candle_does_not_change_historical_analysis
test_future_snapshot_does_not_change_historical_analysis
test_future_canonical_candle_evolution_does_not_change_historical_analysis
```

## Persistência

```text
test_analysis_round_trip
test_same_analysis_is_idempotent
test_conflicting_analysis_is_rejected
test_persisted_analysis_is_immutable
```

## Regressão

Executar novamente os testes relevantes das FASES 4 e 5, especialmente:

```text
get_candles_as_of
FeatureEngine
point-in-time storage
```

---

# 29. Restrições arquiteturais

Continuam obrigatórias:

- domínio independente de infraestrutura;
- AnalysisEngine depois de FeatureEngine;
- AnalysisEngine sem storage;
- AnalysisEngine sem Ground Truth;
- AnalysisEngine sem ReplaySource;
- AnalysisEngine sem OutcomeEvaluator;
- nenhuma consulta temporal feita pelo próprio classificador;
- nenhum dado futuro;
- nenhum ML;
- nenhuma dependência adicional sem necessidade;
- nenhuma alteração da stack congelada.

---

# 30. Fora do escopo da FASE 6

Não implementar:

- OutcomeEvaluator;
- accuracy;
- precision;
- recall;
- matriz de confusão;
- calibração baseada em resultados futuros;
- Dashboard;
- UI de análise;
- sinais de compra ou venda;
- recomendação financeira;
- previsão de preço;
- stop loss;
- take profit;
- gestão de capital;
- corretoras;
- execução;
- dinheiro real;
- notícias;
- sentimento;
- machine learning;
- reinforcement learning;
- novos indicadores;
- FASE 7;
- FASE 8.

---

# 31. Sequência recomendada de implementação

Somente depois de `PHASE_START = READY`.

## Incremento 1

Contratos de domínio:

```text
AnalysisDecision
ajustes finais em Analysis
AnalysisEngine
AnalysisConfig
```

Mais testes unitários da tabela de decisão.

## Incremento 2

Orquestração point-in-time:

```text
get_candles_as_of
→ FeatureEngine
→ data_quality
→ AnalysisEngine
```

Mais testes integrados anti-future-leakage.

## Incremento 3

Persistência de `Analysis`:

```text
StorageProvider
PostgreSQL
migration
immutability/conflict
```

## Incremento 4

Regressão completa e preparação para `chartvision-phase-close`.

Não iniciar FASE 7.

---

# 32. Definition of Done específica

A FASE 6 exige:

```text
contrato implementado
+
quatro estados comprovados
+
UNCERTAIN comprovado
+
determinismo comprovado
+
anti-future-leakage comprovado
+
persistência imutável da Analysis
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

Somente então a FASE 7 poderá ser autorizada.

---

# 33. Resumo normativo

```text
INPUT TEMPORAL
get_candles_as_of(session_id, as_of)

        ↓

FEATURES USADAS
BasicTrend
basic_lateralization

        ↓

QUALITY GATE
minimum_data_quality

        ↓

PRECEDÊNCIA
insufficient
→ low quality
→ SIDEWAYS
→ UP/DOWN
→ UNCERTAIN

        ↓

OUTPUT
AnalysisDecision

        ↓

REGISTRO
Analysis(timestamp = as_of)

        ↓

IMUTÁVEL

        ↓

FASE 7 FUTURA
OutcomeEvaluator
```

O Analysis Lab MVP é deliberadamente simples, determinístico, auditável e point-in-time.
