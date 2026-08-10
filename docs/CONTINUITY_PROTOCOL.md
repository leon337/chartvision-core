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
7. CI, commits, PRs e issues reais relacionados à fase.

Não começar implementação antes dessa leitura.

## 2. GitHub é a fonte de verdade

Quando houver divergência entre conversa e repositório:

- verificar o estado atual no GitHub;
- preferir documentação persistida e evidência técnica;
- não assumir que uma tarefa foi concluída apenas porque foi mencionada em chat.

## 3. Uma fase por missão

Cada missão de implementação deve conter:

- fase autorizada;
- objetivo;
- escopo permitido;
- itens proibidos;
- critérios de aceite;
- testes exigidos;
- definição de PASS/FAIL.

Não antecipar a fase seguinte.

## 4. Loop orientado por objetivo

Fluxo obrigatório:

```text
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
PASS? ── não ──► CORRIGIR ──► TESTAR NOVAMENTE
  │
 sim
  ↓
REGISTRAR EVIDÊNCIA
      ↓
ATUALIZAR MEMÓRIA
      ↓
PRÓXIMA FASE
```

Uma execução bem-sucedida de comando não equivale a objetivo concluído.

## 5. Handoff obrigatório ao concluir uma fase

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
- commit/PR relevante;
- CI relevante;
- limitações conhecidas;
- próxima fase desbloqueada.

## 6. Decisões novas

Se surgir necessidade de alterar arquitetura, stack, sequência ou escopo:

1. parar a alteração;
2. explicar por que a decisão atual é insuficiente;
3. registrar proposta;
4. obter autorização;
5. criar nova entrada em `docs/DECISIONS.md`;
6. atualizar documentos afetados;
7. só então implementar.

## 7. Ideias futuras

Ideias úteis que não pertencem à fase atual não devem ser descartadas nem implementadas.

Devem ser classificadas como `FUTURE`, sem alterar o v1 congelado.

## 8. Protocolo para novo chat

Ao retomar este projeto em novo chat, a primeira ação técnica deve ser consultar o repositório `leon337/chartvision-core` e responder com:

- HEAD atual;
- fase atual;
- último PASS conhecido;
- CI relevante;
- próxima fase;
- bloqueios existentes.

Somente depois continuar o desenvolvimento.

## 9. Protocolo para Codex

Codex deve receber uma missão autocontida, mas ainda assim deve ler `AGENTS.md` e os documentos oficiais.

Codex não está autorizado a:

- redefinir o produto;
- ampliar o escopo;
- pular fases;
- trocar stack sem decisão registrada;
- marcar PASS sem evidência;
- ocultar falhas;
- usar dados futuros em análise;
- acoplar o núcleo a uma fonte específica.

## 10. Regra de memória mínima

O projeto nunca deve depender exclusivamente de memória de chat para saber:

- o que estamos construindo;
- em qual fase estamos;
- o que já foi validado;
- o que está proibido;
- qual é a próxima tarefa.

Essas cinco respostas devem sempre estar recuperáveis apenas pelo GitHub.