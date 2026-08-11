# ChartVision Core — Market Features MVP

## Escopo da FASE 5

Este documento define o contrato funcional canônico da **FASE 5 — MARKET FEATURES MVP**.

A FASE 5 gera somente estas dez características a partir de candles normalizados e temporalmente seguros:

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

Este documento não implementa `MarketFeatures`, `FeatureEngine`, persistência de features, API, análise, previsão, Outcome Evaluation ou Dashboard.

A FASE 6 permanece separada. Em particular, os estados `UP`, `DOWN`, `SIDEWAYS` e `UNCERTAIN` pertencem exclusivamente ao `AnalysisEngine` da FASE 6 e não são valores de nenhuma feature definida aqui.

---

## 1. Fronteira temporal obrigatória

Toda feature da FASE 5 deve começar a partir da leitura point-in-time introduzida no primeiro incremento da fase:

```text
Temporal Memory
    ↓
get_candles_as_of(session_id, as_of)
    ↓
candles conhecidos naquele instante
    ↓
Market Features
```

Contrato obrigatório:

1. `as_of` deve ser timezone-aware; a implementação de storage normaliza o instante para UTC conforme o contrato temporal existente;
2. o conjunto de entrada é o `tuple[Candle, ...]` retornado por `StorageProvider.get_candles_as_of(session_id, as_of)`;
3. somente snapshots cuja `Observation.timestamp <= as_of` podem participar da leitura;
4. nenhum estado canônico posterior, snapshot posterior ou dado do `ReplaySource` pode ser consultado diretamente para calcular features históricas;
5. o resultado de uma feature para um mesmo `session_id`, mesmo `as_of`, mesmos candles retornados e mesmos parâmetros deve ser determinístico;
6. janelas são definidas por quantidade de candles elegíveis, não por duração de relógio;
7. lacunas de candles não são preenchidas, interpoladas ou sintetizadas;
8. quando for necessário um candle anterior, usa-se o candle elegível imediatamente anterior por `open_time` dentro do conjunto point-in-time;
9. adicionar snapshots após `as_of` não pode alterar retrospectivamente qualquer feature calculada para aquele `as_of`.

---

## 2. Política de candle aberto e fechado

A FASE 5 distingue features do estado atual do candle de features estruturais que exigem candles finalizados.

| Categoria | Candle atualmente aberto pode participar? | Regra |
|---|---:|---|
| direção | sim | representa o estado conhecido do candle em `as_of`; é provisório enquanto aberto |
| amplitude | sim | representa a amplitude conhecida em `as_of`; é provisória enquanto aberto |
| retorno | sim, para o candle-alvo | o predecessor usado como denominador deve estar fechado |
| HH / HL / LH / LL | não | ambas as observações comparadas devem representar candles fechados |
| volatilidade simples | não | usa somente candles fechados |
| tendência básica | não | usa somente candles fechados |
| lateralização básica | não | usa somente candles fechados |

Uma feature provisória calculada sobre candle aberto continua válida como fotografia point-in-time daquele instante. Ela não deve ser tratada como valor final do candle.

---

## 3. Política uniforme para histórico insuficiente

O contrato de ausência de valor da FASE 5 é uniforme:

- se a feature não puder ser matematicamente calculada porque faltam candles elegíveis, porque uma precondição temporal não é atendida ou porque um denominador requerido é zero, o valor da feature é `None`;
- não retornar `0`, `False` ou outro valor artificial para representar falta de histórico;
- igualdade válida faz parte da matemática da feature e não é tratada como histórico insuficiente;
- parâmetros de contrato inválidos, como janela menor que o mínimo permitido, threshold negativo ou `as_of` naive, são erro de entrada e devem gerar `ValueError` quando a implementação funcional existir.

Este contrato não redefine o estado sistêmico `INSUFFICIENT_DATA` já previsto no escopo. Aqui, `None` representa somente ausência matemática de uma feature individual.

---

## 4. Política numérica e precisão

### 4.1 Tipos

Resultados numéricos derivados devem usar `Decimal`.

Não converter preços ou resultados intermediários para `float`.

Resultados categóricos e lógicos:

- direção: valor categórico;
- HH / HL / LH / LL: `bool | None`;
- tendência básica: valor categórico ou `None`;
- lateralização básica: `bool | None`.

### 4.2 Contexto decimal

Quando uma operação exigir arredondamento, divisão ou raiz quadrada, a futura implementação deve usar um contexto Decimal local e explícito:

- precisão: `28` dígitos significativos;
- arredondamento: `ROUND_HALF_EVEN`.

Não depender do contexto Decimal global mutável do processo.

Não aplicar `quantize` para escala de apresentação dentro do cálculo das features. Formatação para percentual, casas decimais ou UI pertence às camadas posteriores.

### 4.3 Unidade percentual

Retorno, volatilidade e `range_ratio` de lateralização são armazenados como frações adimensionais.

Exemplo: `0.02` significa `2%`.

A multiplicação por `100` é somente apresentação e não faz parte da fórmula canônica.

---

## 5. Parâmetros explícitos do contrato

Nenhuma janela ou threshold possui default implícito.

Quando a feature exigir configuração, o valor deve ser fornecido explicitamente ao futuro cálculo:

- `volatility_window_candles: int`, com valor mínimo `3`;
- `trend_pairs: int`, com valor mínimo `1`;
- `lateralization_window_candles: int`, com valor mínimo `3`;
- `lateralization_max_range_ratio: Decimal`, com valor mínimo `0`.

Esses parâmetros pertencem ao contrato funcional da FASE 5 e não são novas features.

---

# 6. Definições canônicas

## 6.1 Direção

**Nome:** direção do candle.

**Significado:** relação entre `close` e `open` do mesmo candle no estado conhecido em `as_of`.

**Entrada necessária:** um `Candle` pertencente ao conjunto point-in-time.

**Mínimo de candles:** `1`.

**Candle aberto:** permitido.

**Fórmula / comparação exata:**

```text
se close > open  → CLOSE_ABOVE_OPEN
se close < open  → CLOSE_BELOW_OPEN
se close == open → CLOSE_EQUAL_OPEN
```

**Unidade:** não aplicável.

**Tipo:** valor categórico conceitual `CandleDirection` com exatamente os três valores acima.

**Igualdade:** `close == open` resulta em `CLOSE_EQUAL_OPEN`.

**Histórico insuficiente:** `None` somente se não existir candle-alvo elegível.

**Horizonte temporal:** somente o estado point-in-time do próprio candle em `as_of`.

**Exemplos:**

- `open=100`, `close=103` → `CLOSE_ABOVE_OPEN`;
- `open=100`, `close=97` → `CLOSE_BELOW_OPEN`;
- `open=100`, `close=100` → `CLOSE_EQUAL_OPEN`.

**Future leakage:** se o candle estiver aberto, usa-se exclusivamente o `close` conhecido no snapshot selecionado em `as_of`; um `close` posterior não pode substituir o valor histórico.

---

## 6.2 Amplitude

**Nome:** amplitude absoluta do candle.

**Significado:** faixa total de preço conhecida entre `high` e `low` do mesmo candle.

**Entrada necessária:** um `Candle` pertencente ao conjunto point-in-time.

**Mínimo de candles:** `1`.

**Candle aberto:** permitido.

**Fórmula exata:**

```text
amplitude = high - low
```

**Unidade:** mesma unidade de preço usada pelo `Candle`.

**Tipo:** `Decimal`.

**Igualdade:** se `high == low`, `amplitude = Decimal("0")`.

**Histórico insuficiente:** `None` somente se não existir candle-alvo elegível.

**Horizonte temporal:** somente o estado point-in-time do próprio candle em `as_of`.

**Exemplo:**

```text
high = 105
low  = 98
amplitude = 105 - 98 = 7
```

**Future leakage:** para candle aberto, `high` e `low` são os valores conhecidos em `as_of`; extremos descobertos depois do corte não podem participar.

---

## 6.3 Retorno

**Nome:** retorno simples close-to-close.

**Significado:** variação relativa do `close` do candle-alvo em relação ao `close` do candle elegível imediatamente anterior por `open_time`.

**Entrada necessária:**

- candle-alvo `C_t`;
- candle predecessor elegível `C_(t-1)`.

**Mínimo de candles:** `2`.

**Candle aberto:** o candle-alvo pode estar aberto; o predecessor deve estar fechado. Se o alvo estiver aberto, o retorno é provisório em `as_of`.

**Fórmula exata:**

```text
retorno_t = (close_t - close_(t-1)) / close_(t-1)
```

**Denominador inválido:** se `close_(t-1) == 0`, o retorno é `None`.

**Unidade:** fração adimensional.

**Tipo:** `Decimal | None`.

**Igualdade:** se `close_t == close_(t-1)` e o denominador for não zero, `retorno_t = Decimal("0")`.

**Histórico insuficiente:** `None` se não existir predecessor elegível e fechado.

**Horizonte temporal:** usa somente os dois candles recuperados por `get_candles_as_of(session_id, as_of)`. Não há normalização pela duração temporal entre eles e lacunas não são preenchidas.

**Exemplos:**

```text
close_(t-1) = 100
close_t     = 103
retorno_t   = (103 - 100) / 100 = 0.03
```

```text
close_(t-1) = 100
close_t     = 100
retorno_t   = 0
```

```text
close_(t-1) = 0
close_t     = 10
retorno_t   = None
```

**Future leakage:** se `C_t` estiver aberto, usa-se somente seu `close` point-in-time; evolução posterior do mesmo candle não pode alterar o retorno histórico calculado em `as_of`.

---

## 6.4 Volatilidade simples

**Nome:** volatilidade simples de retornos close-to-close.

**Significado:** desvio padrão populacional dos retornos simples entre closes consecutivos dos últimos candles fechados elegíveis.

**Entrada necessária:** últimos `volatility_window_candles = N` candles fechados do conjunto point-in-time, em ordem crescente de `open_time`.

**Parâmetro:** `N >= 3`.

**Mínimo de candles:** `N`; portanto existem `M = N - 1 >= 2` retornos.

**Candle aberto:** não participa.

**Série utilizada:** para candles fechados `C_1 ... C_N`:

```text
r_i = (close_i - close_(i-1)) / close_(i-1), para i = 2 ... N
M = N - 1
```

Se qualquer `close_(i-1) == 0`, a volatilidade inteira da janela é `None`.

**Média dos retornos:**

```text
mu = (1 / M) * Σ r_i
```

**Variância populacional:**

```text
variance = (1 / M) * Σ (r_i - mu)^2
```

**Volatilidade:**

```text
volatilidade = sqrt(variance)
```

A divisão usa `M`, e não `M - 1`. Portanto a definição é explicitamente **populacional**, não amostral.

**Unidade:** fração adimensional.

**Tipo:** `Decimal | None`.

**Igualdade:** se todos os retornos da janela forem idênticos, `volatilidade = Decimal("0")`.

**Histórico insuficiente:** `None` quando existirem menos de `N` candles fechados elegíveis.

**Horizonte temporal:** a janela é o sufixo dos últimos `N` candles fechados disponíveis em `get_candles_as_of(session_id, as_of)`; candles abertos e snapshots posteriores são excluídos.

**Exemplo verificável:**

Para `N = 3` e closes fechados `[100, 110, 99]`:

```text
r_2 = (110 - 100) / 100 = 0.10
r_3 = (99 - 110) / 110 = -0.10
mu = (0.10 + -0.10) / 2 = 0
variance = ((0.10)^2 + (-0.10)^2) / 2 = 0.01
volatilidade = sqrt(0.01) = 0.10
```

**Future leakage:** somente candles fechados já presentes no conjunto point-in-time podem compor a janela; um candle fechado depois de `as_of` não pode retroagir para dentro da janela histórica.

---

## 6.5 HH — Higher High

**Nome:** HH.

**Significado:** informa se o `high` do candle fechado atual é estritamente maior que o `high` do candle fechado elegível imediatamente anterior.

**Entrada necessária:** dois candles fechados consecutivos na sequência elegível: `C_prev` e `C_curr`.

**Mínimo de candles:** `2` fechados.

**Candle aberto:** não participa.

**Comparação exata:**

```text
HH = current.high > previous.high
```

**Unidade:** não aplicável.

**Tipo:** `bool | None`.

**Igualdade:** se `current.high == previous.high`, `HH = False`.

**Histórico insuficiente:** `None` se não existirem dois candles fechados elegíveis.

**Horizonte temporal:** os dois candles devem vir do conjunto point-in-time em `as_of`.

**Exemplo:** `previous.high=105`, `current.high=107` → `HH=True`.

**Future leakage:** highs posteriores do candle atual não são permitidos porque HH só é calculado quando o candle atual já está fechado no horizonte consultado.

---

## 6.6 HL — Higher Low

**Nome:** HL.

**Significado:** informa se o `low` do candle fechado atual é estritamente maior que o `low` do candle fechado elegível imediatamente anterior.

**Entrada necessária:** `C_prev` e `C_curr`, ambos fechados.

**Mínimo de candles:** `2` fechados.

**Candle aberto:** não participa.

**Comparação exata:**

```text
HL = current.low > previous.low
```

**Unidade:** não aplicável.

**Tipo:** `bool | None`.

**Igualdade:** se `current.low == previous.low`, `HL = False`.

**Histórico insuficiente:** `None` se não existirem dois candles fechados elegíveis.

**Horizonte temporal:** comparação point-in-time dos dois candles fechados elegíveis.

**Exemplo:** `previous.low=95`, `current.low=96` → `HL=True`.

**Future leakage:** nenhum low descoberto depois de `as_of` participa.

---

## 6.7 LH — Lower High

**Nome:** LH.

**Significado:** informa se o `high` do candle fechado atual é estritamente menor que o `high` do candle fechado elegível imediatamente anterior.

**Entrada necessária:** `C_prev` e `C_curr`, ambos fechados.

**Mínimo de candles:** `2` fechados.

**Candle aberto:** não participa.

**Comparação exata:**

```text
LH = current.high < previous.high
```

**Unidade:** não aplicável.

**Tipo:** `bool | None`.

**Igualdade:** se `current.high == previous.high`, `LH = False`.

**Histórico insuficiente:** `None` se não existirem dois candles fechados elegíveis.

**Horizonte temporal:** comparação point-in-time dos dois candles fechados elegíveis.

**Exemplo:** `previous.high=105`, `current.high=103` → `LH=True`.

**Future leakage:** nenhum high posterior ao corte participa.

---

## 6.8 LL — Lower Low

**Nome:** LL.

**Significado:** informa se o `low` do candle fechado atual é estritamente menor que o `low` do candle fechado elegível imediatamente anterior.

**Entrada necessária:** `C_prev` e `C_curr`, ambos fechados.

**Mínimo de candles:** `2` fechados.

**Candle aberto:** não participa.

**Comparação exata:**

```text
LL = current.low < previous.low
```

**Unidade:** não aplicável.

**Tipo:** `bool | None`.

**Igualdade:** se `current.low == previous.low`, `LL = False`.

**Histórico insuficiente:** `None` se não existirem dois candles fechados elegíveis.

**Horizonte temporal:** comparação point-in-time dos dois candles fechados elegíveis.

**Exemplo:** `previous.low=95`, `current.low=93` → `LL=True`.

**Future leakage:** nenhum low posterior ao corte participa.

### Independência das dimensões HH/LH e HL/LL

As comparações de high e low são independentes.

Para cada par fechado:

- exatamente uma de `HH` ou `LH` pode ser `True`, ou ambas são `False` quando os highs são iguais;
- exatamente uma de `HL` ou `LL` pode ser `True`, ou ambas são `False` quando os lows são iguais;
- combinações cruzadas como `HH=True` e `LL=True` são válidas e não devem ser corrigidas ou reinterpretadas.

Exemplo completo:

```text
previous: high=105, low=95
current:  high=107, low=96

HH=True
LH=False
HL=True
LL=False
```

Com `current.high=105`, tanto `HH` quanto `LH` são `False` para a dimensão de high.

---

## 6.9 Tendência básica

**Nome:** tendência estrutural básica.

**Significado:** resume se uma sequência recente de pares de candles fechados apresenta estrutura estritamente ascendente em high e low, estritamente descendente em high e low, ou qualquer outra combinação.

Essa feature é estrutural e não é a classificação de mercado da FASE 6.

**Entrada necessária:** últimos `trend_pairs + 1` candles fechados elegíveis, em ordem crescente de `open_time`.

**Parâmetro:** `trend_pairs = P`, com `P >= 1`.

**Mínimo de candles:** `P + 1` fechados.

**Candle aberto:** não participa.

**Features anteriores utilizadas:** para cada par adjacente são usadas exatamente as comparações HH, HL, LH e LL definidas neste documento.

**Regra determinística:**

Para cada um dos `P` pares adjacentes:

```text
par ascendente  ⇔ HH == True e HL == True
par descendente ⇔ LH == True e LL == True
```

O resultado da janela é:

```text
se todos os P pares forem ascendentes  → RISING_STRUCTURE
se todos os P pares forem descendentes → FALLING_STRUCTURE
caso contrário                          → MIXED_STRUCTURE
```

**Valores possíveis:**

- `RISING_STRUCTURE`;
- `FALLING_STRUCTURE`;
- `MIXED_STRUCTURE`.

Nenhum desses valores equivale a `UP`, `DOWN`, `SIDEWAYS` ou `UNCERTAIN`.

**Unidade:** não aplicável.

**Tipo:** valor categórico conceitual `BasicTrend | None`.

**Igualdade:** qualquer igualdade de high ou low torna aquele par não estritamente ascendente e não estritamente descendente; se isso ocorrer em qualquer par da janela, o resultado da janela é `MIXED_STRUCTURE`.

Combinações cruzadas como `HH=True` + `LL=True` ou `LH=True` + `HL=True` também resultam em `MIXED_STRUCTURE`.

**Histórico insuficiente:** `None` com menos de `P + 1` candles fechados elegíveis.

**Horizonte temporal:** usa o sufixo dos últimos `P + 1` candles fechados do conjunto point-in-time.

**Exemplo ascendente:** para `P=2`:

```text
C1: high=105, low=95
C2: high=106, low=96
C3: high=107, low=97

C1→C2: HH=True, HL=True
C2→C3: HH=True, HL=True
resultado: RISING_STRUCTURE
```

**Exemplo descendente:** para `P=2`:

```text
C1: high=105, low=95
C2: high=104, low=94
C3: high=103, low=93

resultado: FALLING_STRUCTURE
```

**Exemplo misto:** para `P=1`:

```text
C1: high=105, low=95
C2: high=107, low=93

HH=True e LL=True
resultado: MIXED_STRUCTURE
```

**Future leakage:** somente candles já fechados em `as_of` podem compor os pares; fechar ou evoluir candles depois do corte não pode mudar a tendência histórica daquele horizonte.

---

## 6.10 Lateralização básica

**Nome:** lateralização estrutural básica.

**Significado:** indica se uma janela recente de candles fechados possui simultaneamente:

1. ausência de estrutura estritamente ascendente ou estritamente descendente em toda a janela; e
2. faixa total normalizada menor ou igual a um threshold explícito.

Esta feature é apenas uma característica estrutural booleana da FASE 5. Ela não produz o estado `SIDEWAYS` da FASE 6.

**Entrada necessária:** últimos `lateralization_window_candles = N` candles fechados elegíveis, com `N >= 3`.

**Parâmetros:**

- `lateralization_window_candles = N`, `N >= 3`;
- `lateralization_max_range_ratio = T`, `T >= 0`.

**Mínimo de candles:** `N` fechados.

**Candle aberto:** não participa.

**Relação com tendência básica:** dentro da mesma janela, a tendência básica é avaliada com `trend_pairs = N - 1`.

**Faixa da janela:**

```text
window_high = max(high_1 ... high_N)
window_low  = min(low_1 ... low_N)
window_range = window_high - window_low
```

**Preço de referência:**

```text
reference_price = abs(close_1)
```

onde `close_1` é o close do primeiro candle da janela.

Se `reference_price == 0`, a lateralização é `None`.

**Faixa normalizada:**

```text
range_ratio = window_range / reference_price
```

**Regra determinística:**

```text
lateralizacao =
    True,  se tendencia_basica == MIXED_STRUCTURE
           e range_ratio <= T

    False, se tendencia_basica == RISING_STRUCTURE
           ou tendencia_basica == FALLING_STRUCTURE
           ou range_ratio > T
```

Se qualquer precondição matemática da janela não existir, o resultado é `None`.

**Unidade do threshold:** fração adimensional; `T=0.01` significa `1%`.

**Tipo:** `bool | None`.

**Igualdade:** `range_ratio == T` satisfaz o limite e pode resultar em `True` se a tendência da mesma janela for `MIXED_STRUCTURE`.

**Histórico insuficiente:** `None` com menos de `N` candles fechados elegíveis.

**Horizonte temporal:** usa o sufixo dos últimos `N` candles fechados do conjunto point-in-time.

**Exemplo no limite:**

Para `N=3`, `T=0.01`:

```text
C1: high=100.5, low=99.5, close=100
C2: high=100.5, low=99.5, close=100
C3: high=100.5, low=99.5, close=100

window_high = 100.5
window_low = 99.5
window_range = 1.0
reference_price = 100
range_ratio = 1.0 / 100 = 0.01
```

Os highs e lows iguais fazem com que os pares não sejam estritamente ascendentes nem descendentes, portanto a tendência básica da janela é `MIXED_STRUCTURE`.

Como `range_ratio == T`, `lateralizacao = True`.

Com os mesmos candles e `T=0.009`, `range_ratio > T`, então `lateralizacao = False`.

**Future leakage:** a janela contém somente candles fechados disponíveis em `get_candles_as_of(session_id, as_of)`; nenhum candle ou extremo de preço observado depois do corte pode reduzir, ampliar ou reclassificar retrospectivamente a janela.

---

## 7. Resumo de mínimos e tipos

| Feature | Mínimo | Candle aberto | Resultado |
|---|---:|---:|---|
| direção | 1 candle | sim | `CandleDirection | None` |
| amplitude | 1 candle | sim | `Decimal | None` |
| retorno | alvo + predecessor fechado | alvo sim | `Decimal | None` |
| volatilidade simples | `N >= 3` fechados | não | `Decimal | None` |
| HH | 2 fechados | não | `bool | None` |
| HL | 2 fechados | não | `bool | None` |
| LH | 2 fechados | não | `bool | None` |
| LL | 2 fechados | não | `bool | None` |
| tendência básica | `P + 1`, `P >= 1`, fechados | não | `BasicTrend | None` |
| lateralização básica | `N >= 3` fechados | não | `bool | None` |

---

## 8. Regras de implementação futura

Quando o código funcional da FASE 5 for autorizado, deverá respeitar estas regras:

1. domínio puro, sem dependência de SQLAlchemy/PostgreSQL;
2. storage acessado pelo contrato `StorageProvider`;
3. `get_candles_as_of(session_id, as_of)` é a fronteira temporal de entrada;
4. nenhuma leitura direta de `ReplaySource` ou Ground Truth;
5. nenhuma leitura histórica a partir do estado canônico atual de `candles`;
6. nenhuma feature adicional além das dez autorizadas;
7. nenhuma classificação da FASE 6;
8. todos os cálculos devem possuir testes unitários determinísticos;
9. testes anti-future-leakage devem demonstrar que dados posteriores ao horizonte não alteram resultados históricos;
10. nenhuma persistência de features deve ser inferida deste documento; persistência será tratada somente quando explicitamente autorizada dentro do escopo da FASE 5.

---

## 9. Consistência com documentos oficiais

Esta especificação preserva:

- `docs/SCOPE.md`: somente `MarketFeatures` simples do v1, sem indicadores adicionais, sem integrações externas e sem Ground Truth como atalho;
- `docs/ROADMAP.md`: exatamente direção, amplitude, retorno, volatilidade simples, HH/HL/LH/LL, tendência básica e lateralização básica;
- `docs/DECISIONS.md`: núcleo desacoplado, PostgreSQL atrás de contrato, memória temporal auditável e ausência de future leakage;
- `docs/architecture.md`: `TemporalMemory → FeatureEngine → AnalysisEngine`, com domínio independente de infraestrutura e sem antecipação da FASE 6;
- `docs/temporal_memory.md`: candles canônicos e snapshots permanecem imutáveis conforme o contrato da FASE 4;
- modelo `Candle`: nenhum campo ou tipo existente é alterado;
- `StorageProvider`: `get_candles_as_of(session_id, as_of)` é adotado como entrada temporal canônica.

Não há decisão arquitetural transversal nova neste documento. Por isso `docs/DECISIONS.md` não precisa ser alterado por este incremento.

---

## 10. Fora do escopo deste incremento

Não implementar neste incremento:

- `MarketFeatures` em Python;
- `FeatureEngine` funcional;
- testes executando fórmulas;
- tabela ou migration de features;
- persistência de features;
- API ou endpoints;
- `AnalysisEngine`;
- `UP/DOWN/SIDEWAYS/UNCERTAIN` como feature;
- previsão ou sinais financeiros;
- Outcome Evaluation;
- Dashboard;
- Ground Truth;
- acesso ao `ReplaySource`;
- indicadores adicionais.

A FASE 5 permanece aberta após este documento. Nenhum `PHASE CLOSE` é realizado por esta especificação.
