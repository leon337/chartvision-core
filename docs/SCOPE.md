# ChartVision Core — Escopo Congelado v1

> Este arquivo define o que o projeto **é** e o que ele **não é** durante o v1.
>
> Alterações de escopo exigem autorização explícita, registro em `docs/DECISIONS.md`, atualização deste arquivo e revisão de `docs/ROADMAP.md`.

## Missão do v1

Construir um laboratório reproduzível capaz de:

1. exibir um gráfico de candles em ambiente controlado;
2. observar visualmente o gráfico em intervalos regulares;
3. transformar elementos visuais em dados estruturados;
4. reconstruir candles;
5. manter memória temporal;
6. gerar características de mercado simples;
7. produzir uma classificação experimental do estado do gráfico;
8. registrar a classificação;
9. verificar posteriormente o resultado;
10. medir a qualidade do sistema.

## Princípio de produto

O projeto constrói um **motor universal de leitura e interpretação de gráficos**, e não um sistema acoplado a uma plataforma específica.

A fonte inicial do v1 é um ambiente de replay controlado. Integrações externas ficam fora do escopo do v1.

## Decisões congeladas do MVP

- uma única fonte: `ReplaySource`;
- um único gráfico por sessão;
- candles;
- um único ativo por sessão;
- timeframe inicial de 1 minuto;
- captura visual padrão a cada 5 segundos;
- tema visual controlado;
- tamanho de gráfico controlado;
- cores de candle conhecidas;
- sem volume no MVP;
- sem indicadores gráficos adicionais no MVP;
- sem múltiplos painéis;
- banco PostgreSQL;
- backend Python + FastAPI;
- frontend React + TypeScript + Vite;
- visão computacional com OpenCV;
- gráfico controlado com TradingView Lightweight Charts ou abstração equivalente aprovada sem alterar o contrato arquitetural;
- Ground Truth separado do leitor visual.

## Princípio de Ground Truth

O `ReplaySource` conhece os OHLC reais usados para renderizar o gráfico, porém o módulo de visão não pode acessar esses dados.

Fluxo obrigatório:

```text
ReplaySource ───────► Ground Truth
     │
     ▼
ChartRenderer
     │
     ▼
IMAGEM
     │
     ▼
ChartObserver / OpenCV
     │
     ▼
Normalizer
```

O Ground Truth existe para avaliação, não para auxiliar a leitura visual.

## Formato canônico

Todo dado que entra no núcleo deve ser normalizado para contratos internos independentes da fonte.

Entidades principais:
- Session;
- Frame;
- Observation;
- Candle;
- MarketFeatures;
- Analysis;
- Outcome.

## Regra crítica: frame não é candle

Capturas periódicas representam observações do estado da tela. Várias capturas podem corresponder ao mesmo candle ainda aberto.

O sistema deve rastrear identidade temporal e impedir duplicação de candles.

## Qualidade dos dados

Toda informação derivada de visão deve possuir indicador de confiança/qualidade.

Se a leitura não for confiável, o comportamento correto é recusar ou marcar como incerto. Dados ausentes nunca devem ser inventados.

Estados de falha previstos incluem:
- `CHART_NOT_FOUND`;
- `LOW_IMAGE_QUALITY`;
- `PRICE_SCALE_NOT_FOUND`;
- `CANDLE_DETECTION_FAILED`;
- `TRACKING_LOST`;
- `INSUFFICIENT_DATA`;
- `ANALYSIS_UNCERTAIN`.

## Fora do escopo do v1

É proibido adicionar sem nova decisão de escopo:

- integração com corretoras ou plataformas externas;
- automação de login;
- execução de ordens;
- compra ou venda;
- uso de dinheiro real;
- controle de mouse/teclado de plataformas externas;
- múltiplas plataformas;
- múltiplos timeframes simultâneos;
- múltiplos gráficos simultâneos;
- aplicativo mobile;
- notificações;
- Telegram;
- WhatsApp;
- agentes autônomos;
- aprendizado online automático;
- treinamento automático de modelos;
- reinforcement learning;
- dezenas de indicadores;
- notícias;
- análise fundamentalista;
- sentimento de mercado;
- gestão de carteira;
- gestão financeira;
- copy trading;
- ranking social;
- assinatura e pagamentos;
- multiusuário.

## Política contra scope creep

Quando surgir uma ideia nova durante a implementação:

1. não implementar imediatamente;
2. registrar como proposta futura;
3. verificar se altera o objetivo da fase atual;
4. manter a fase atual intacta;
5. somente incorporar após autorização explícita e atualização dos documentos oficiais.

## Fontes de verdade — ordem de precedência

Em caso de conflito:

1. `docs/SCOPE.md` — limites do produto;
2. `docs/ROADMAP.md` — ordem e critérios das fases;
3. `docs/DECISIONS.md` — decisões arquiteturais aprovadas;
4. `docs/PROJECT_STATE.md` — estado operacional atual;
5. `docs/architecture.md` — estrutura técnica;
6. issue-mestra do roadmap;
7. código e testes;
8. conversas externas.

Conversas de chat não substituem documentação persistida no repositório.