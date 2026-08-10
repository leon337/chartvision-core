# AGENTS.md — ChartVision Core

Estas instruções se aplicam a qualquer agente, Codex ou automação que trabalhe neste repositório.

## Fonte de verdade

Antes de alterar código, leia nesta ordem:

1. `docs/PROJECT_STATE.md`
2. `docs/SCOPE.md`
3. `docs/ROADMAP.md`
4. `docs/DECISIONS.md`
5. `docs/CONTINUITY_PROTOCOL.md`
6. documentação específica da fase atual
7. `docs/CHATGPT_PROJECT_INSTRUCTIONS.md`, quando o trabalho vier de um Projeto do ChatGPT

Depois consulte o estado real do GitHub: branch, HEAD, CI, issue mestra, issues e PRs relevantes.

## Regra principal

Implemente **somente a fase atualmente autorizada**.

Não:
- aumente escopo;
- antecipe fases;
- trabalhe em duas fases no mesmo ciclo de implementação;
- troque stack sem decisão registrada;
- adicione integração externa no v1;
- marque fase como concluída sem testes e evidência;
- use Ground Truth dentro do módulo de visão;
- introduza future leakage;
- altere retrospectivamente análises registradas.

## Organização dos chats/sessões

O desenvolvimento utiliza preferencialmente **um chat dedicado por fase**.

O chat da FASE 0 é o espaço de Foundation/governança e pode receber decisões transversais, mas não deve implementar funcionalidades das fases 1–8.

Cada fase seguinte deve iniciar em um novo chat/sessão depois que a fase anterior estiver formalmente encerrada.

Chats são ambiente de trabalho. GitHub é memória oficial.

## Skills de lifecycle

As skills oficiais do repositório são:

- `.agents/skills/chartvision-phase-start/SKILL.md`
- `.agents/skills/chartvision-phase-close/SKILL.md`

Antes de planejar/implementar uma fase, execute ou reproduza o procedimento `chartvision-phase-start`.

Antes de declarar uma fase concluída, execute ou reproduza o procedimento `chartvision-phase-close`.

Uma skill nunca substitui os documentos oficiais nem permite ignorar evidências reais.

## Estado inicial registrado

A FASE 0 — Foundation está concluída e validada.
A próxima fase prevista é FASE 1 — Replay MVP.

Este trecho é apenas referência histórica. Sempre confirme o estado em `docs/PROJECT_STATE.md` e no GitHub antes de agir.

## Método de trabalho

Para cada fase:

1. execute PHASE START;
2. inspecione o estado real;
3. confronte a missão com o escopo;
4. implemente a menor solução que satisfaz os critérios;
5. execute testes;
6. observe evidências;
7. corrija até satisfazer os critérios;
8. execute PHASE CLOSE;
9. atualize a memória persistente;
10. somente então encerre a fase.

## Handoff obrigatório

Ao concluir trabalho relevante, informe e persista:

- arquivos/componentes alterados;
- testes executados;
- resultados;
- commit/PR/HEAD;
- CI;
- critérios de aceite;
- pendências/limitações;
- estado da fase;
- próxima ação autorizada.

Consulte `docs/CONTINUITY_PROTOCOL.md` para o protocolo completo.
