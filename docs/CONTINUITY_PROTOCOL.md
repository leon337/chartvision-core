# ChartVision Core — Protocolo de Continuidade

Objetivo: impedir perda de contexto, regressão de decisões e desvio de escopo entre chats, agentes, Codex e sessões futuras.

## 1. Leitura obrigatória antes de qualquer trabalho

Todo agente deve ler, nesta ordem:

1. `AGENTS.md`;
2. `docs/PROJECT_STATE.md`;
3. `docs/SCOPE.md`;
4. `docs/ROADMAP.md`;
5. `docs/DECISIONS.md`;
6. documentação específica da fase;
7. `docs/CHATGPT_PROJECT_INSTRUCTIONS.md`, quando aplicável;
8. CI, commits, PRs e issues reais relacionados à fase.

Não começar implementação antes dessa leitura.

## 2. GitHub é a fonte de verdade

Quando houver divergência entre conversa e repositório:

- verificar o estado atual no GitHub;
- preferir documentação persistida e evidência técnica;
- não assumir que uma tarefa foi concluída apenas porque foi mencionada em chat.

Se os próprios documentos oficiais divergirem, parar a implementação, identificar a inconsistência e corrigir a governança antes de continuar.

## 3. Um chat por fase

O desenvolvimento utiliza preferencialmente um chat/sessão dedicado para cada fase do roadmap.

Padrão:

```text
FASE 0 — Foundation / Governança
FASE 1 — Replay MVP
FASE 2 — Visual Observer MVP
FASE 3 — Candle Reconstruction MVP
FASE 4 — Temporal Memory MVP
FASE 5 — Market Features MVP
FASE 6 — Analysis Lab MVP
FASE 7 — Outcome Evaluation MVP
FASE 8 — Dashboard MVP
```

O chat da FASE 0 pode tratar governança transversal após seu PASS, mas não implementa funcionalidades das fases posteriores.

Nenhum chat deve implementar duas fases.

Ao concluir uma fase, persistir o handoff no GitHub e abrir um novo chat para a fase seguinte.

## 4. Lifecycle padronizado por skills

O repositório mantém:

- `.agents/skills/chartvision-phase-start/SKILL.md`;
- `.agents/skills/chartvision-phase-close/SKILL.md`.

### PHASE START

Antes de planejar ou implementar:

1. recuperar estado real;
2. confirmar repositório, branch, HEAD e CI;
3. validar fase autorizada;
4. carregar escopo, roadmap, decisões e documentação específica;
5. identificar critérios de aceite/testes/bloqueios;
6. produzir Phase Brief.

Se houver inconsistência, a implementação fica bloqueada.

### PHASE CLOSE

Antes de marcar PASS:

1. revisar implementação e diff;
2. revisar scope creep;
3. executar testes;
4. verificar CI do estado fechado;
5. verificar cada critério de aceite;
6. verificar regressões;
7. atualizar documentação específica;
8. atualizar `PROJECT_STATE.md`;
9. atualizar `ROADMAP.md`;
10. atualizar Issue Mestra #1;
11. registrar decisões novas quando aplicável;
12. produzir handoff.

Sem `PHASE_CLOSE = PASS`, a fase continua aberta.

## 5. Uma fase por missão

Cada missão de implementação deve conter:

- fase autorizada;
- objetivo;
- escopo permitido;
- itens proibidos;
- critérios de aceite;
- testes exigidos;
- definição de PASS/FAIL.

Não antecipar a fase seguinte.

## 6. Loop orientado por objetivo

```text
PHASE START
      ↓
OBJETIVO DA FASE
      ↓
INSPECIONAR ESTADO REAL
      ↓
IMPLEMENTAR
      ↓
EXECUTAR TESTES
      ↓
OBSERVAR RESULTADO
      ↓
COMPARAR COM CRITÉRIOS
      ↓
PASS TÉCNICO? ── não ──► CORRIGIR ──► TESTAR NOVAMENTE
      │
     sim
      ↓
PHASE CLOSE
      ↓
ATUALIZAR MEMÓRIA
      ↓
PASS FORMAL
      ↓
NOVO CHAT DA PRÓXIMA FASE
```

Uma execução bem-sucedida de comando não equivale a objetivo concluído.

## 7. Handoff obrigatório ao concluir uma fase

Antes de considerar uma fase encerrada, atualizar:

- `docs/PROJECT_STATE.md`;
- `docs/ROADMAP.md`;
- documentação específica da fase;
- issue-mestra;
- PR/issue da fase, quando existir.

O handoff deve registrar:

- o que foi implementado;
- o que foi testado;
- evidências;
- commit/PR/HEAD relevante;
- CI relevante;
- critérios de aceite;
- limitações conhecidas;
- próxima fase desbloqueada.

## 8. Decisões novas

Se surgir necessidade de alterar arquitetura, stack, sequência, lifecycle ou escopo:

1. parar a alteração;
2. explicar por que a decisão atual é insuficiente;
3. registrar proposta;
4. obter autorização;
5. criar nova entrada em `docs/DECISIONS.md`;
6. atualizar documentos afetados;
7. só então implementar.

## 9. Ideias futuras

Ideias úteis que não pertencem à fase atual não devem ser descartadas nem implementadas.

Devem ser classificadas como `FUTURE`, sem alterar o v1 congelado.

## 10. Protocolo para novo chat

A primeira ação técnica de um novo chat de fase deve ser consultar o repositório e executar/reproduzir `chartvision-phase-start`.

O primeiro resumo deve informar:

- fase solicitada;
- HEAD atual;
- branch;
- último PASS conhecido;
- CI relevante;
- próxima fase autorizada;
- critérios principais;
- bloqueios existentes.

Somente depois continuar o desenvolvimento.

## 11. Protocolo para Codex

Codex deve receber uma missão autocontida e ainda assim ler `AGENTS.md` e os documentos oficiais.

Sempre que a superfície suportar skills, iniciar a missão com `chartvision-phase-start` e encerrar a avaliação com `chartvision-phase-close`.

Codex não está autorizado a:

- redefinir o produto;
- ampliar o escopo;
- pular fases;
- trocar stack sem decisão registrada;
- marcar PASS sem evidência;
- ocultar falhas;
- usar dados futuros em análise;
- acoplar o núcleo a uma fonte específica.

## 12. Regra de memória mínima

O projeto nunca deve depender exclusivamente de memória de chat para saber:

- o que estamos construindo;
- em qual fase estamos;
- o que já foi validado;
- o que está proibido;
- qual é a próxima tarefa.

Essas respostas devem ser recuperáveis apenas pelo GitHub.

## 13. Instrução do Projeto ChatGPT

A versão canônica da instrução usada no Projeto do ChatGPT fica em `docs/CHATGPT_PROJECT_INSTRUCTIONS.md`.

Quando essa instrução for alterada na interface do ChatGPT, atualizar também a cópia canônica no repositório para evitar deriva entre configuração externa e memória oficial.
