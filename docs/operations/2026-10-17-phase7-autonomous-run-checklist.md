# MCF — Checklist de recuperação e CI da Fase 7

Data: 2026-10-17. Executor operacional: MESTRE, com especialistas executados como papéis na mesma sessão; nenhuma execução cognitiva independente declarada.

## Objetivo e limites

Retomar o ChartVision Core e corrigir o CI da Fase 7, preservar tracking de exposição e provenance, registrar evidências e preparar a transferência para o sandbox nativo do ChatGPT. Não iniciar a Fase 8 enquanto o PHASE_CLOSE da Fase 7 não for PASS.

## Checklist rastreável

- [x] Consultar contrato MCF de autoridade, AGENTS.md, PROJECT_STATE, SCOPE, ROADMAP, DECISIONS, CONTINUITY_PROTOCOL e fase atual.
- [x] Conferir GitHub vivo: `main@02afbfb2`, `phase-7-outcome-evaluation-mvp@e979d7e1`, CI quebrado no run 32430442424.
- [x] Identificar o problema: `test_replay_api.py` usa `Phase7OutcomePostgresStorageRepository`; o job backend não oferece banco PostgreSQL e falha por DNS do host `postgres`.
- [x] Criar uma branch de reparo isolada a partir do HEAD exato da Fase 7.
- [x] Alterar exclusivamente configuração CI para provisionar PostgreSQL 16, `DATABASE_URL` no localhost e executar `alembic upgrade head` antes de `pytest`. Sem downgrade de garantias da Fase 7.
- [ ] Confirmar a execução do GitHub Actions no SHA final (backend, frontend, governança, Docker foundation).
- [ ] Corrigir regressões adicionais apenas com evidências verificadas.
- [ ] Obter checkout Git verificável no sandbox `/mnt/data/chartvision-core-workspace`. **PENDENTE:** DNS externo indisponível no contêiner. Checkout separado já existe no dispositivo remoto autorizado, não é o mesmo sandbox.
- [ ] Executar revisão dos 80 critérios da Fase 7 + PHASE_CLOSE formal; somente então solicitar integração funcional.
- [ ] Iniciar Fase 8 em ciclo dedicado apenas após PASS formal da Fase 7.

## Critérios de aceite imediatos

1. GitHub Actions da branch de correção mostra `SUCCESS` para jobs backend, frontend, governance e foundation.
2. Os dois testes de replay anteriormente falhos terminam sem erro de conexão PostgreSQL.
3. Nenhuma alteração indevida a lógica de exposição, Ground Truth ou resultado.
4. PR e referências a commit SHA e CI são verificáveis; estado não se declara concluído antes dessas evidências.

## Restrições e gate

- GitHub é fonte de verdade; este checklist não substitui contrato de fase.
- Não marcar Fase 7 PASS com CI vermelho.
- Não tratar checkout remoto como checkout do sandbox ChatGPT.
- Não realizar merge em `main` nem publicar release sem os gates aplicáveis.
- Estado deste documento: CHECKPOINT DE EXECUÇÃO, NÃO CONCLUSÃO FORMAL.
