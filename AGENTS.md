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

Depois consulte o estado real do GitHub: branch, HEAD, CI, issues e PRs relevantes.

## Regra principal

Implemente **somente a fase atualmente autorizada**.

Não:
- aumente escopo;
- antecipe fases;
- troque stack sem decisão registrada;
- adicione integração externa no v1;
- marque fase como concluída sem testes e evidência;
- use Ground Truth dentro do módulo de visão;
- introduza future leakage;
- altere retrospectivamente análises registradas.

## Estado inicial registrado

A FASE 0 — Foundation está concluída e validada.
A próxima fase prevista é FASE 1 — Replay MVP.
Sempre confirme isso em `docs/PROJECT_STATE.md` e no GitHub antes de agir.

## Método de trabalho

Para cada fase:

1. inspecione o estado real;
2. confronte a tarefa com o escopo;
3. implemente a menor solução que satisfaz os critérios;
4. execute testes;
5. observe evidências;
6. corrija até PASS;
7. atualize a documentação de continuidade;
8. somente então encerre a fase.

## Handoff obrigatório

Ao concluir trabalho relevante, informe e persista:

- arquivos alterados;
- testes executados;
- resultados;
- commit/PR;
- CI;
- pendências;
- estado da fase;
- próxima ação autorizada.

Consulte `docs/CONTINUITY_PROTOCOL.md` para o protocolo completo.