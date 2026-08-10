# ChartVision Core — Estado Atual

> Este é o ponto de retomada operacional do projeto.
>
> Sempre ler este arquivo antes de iniciar uma nova missão.

## Estado atual

- **Versão de planejamento:** v1 congelado
- **Fase atual concluída:** FASE 0 — FOUNDATION
- **Status:** ✅ PASS
- **Próxima fase autorizável:** FASE 1 — REPLAY MVP
- **Fases posteriores:** bloqueadas até PASS sequencial

## Evidência da FASE 0

A Foundation possui:
- FastAPI;
- React + TypeScript + Vite;
- PostgreSQL;
- Docker Compose;
- health check;
- testes backend;
- build frontend;
- lint;
- CI;
- validação da stack completa em Docker.

O CI #7 passou no commit:

`f82877b63229eecaa17ec2db52b731a48d91dac4`

Após esse commit foram adicionados somente documentos de governança/memória; nenhuma funcionalidade de FASE 1 foi implementada.

## Próxima missão prevista

### FASE 1 — Replay MVP

Implementar exclusivamente:
- `ReplaySource`;
- dataset de referência;
- `ChartRenderer`;
- iniciar;
- pausar;
- continuar;
- reiniciar;
- replay determinístico.

### Não implementar na FASE 1
- OpenCV;
- captura visual;
- OCR;
- reconstrução de candles por imagem;
- banco temporal funcional além do necessário à Foundation;
- features;
- AnalysisEngine;
- OutcomeEvaluator;
- integrações externas.

## Gate da FASE 1

A fase somente poderá ser marcada como PASS quando:

1. replay for determinístico;
2. o mesmo dataset produzir a mesma sequência;
3. os controles funcionarem;
4. testes passarem;
5. CI passar;
6. não houver vazamento de dados futuros;
7. documentação da fase for atualizada;
8. este arquivo for atualizado para apontar a próxima fase.

## Estado de implementação por fase

| Fase | Estado | Observação |
|---|---|---|
| 0 — Foundation | ✅ PASS | Validada em CI e Docker |
| 1 — Replay | ⬜ PENDING | Próxima |
| 2 — Visual Observer | 🔒 BLOCKED | Aguarda FASE 1 |
| 3 — Candle Reconstruction | 🔒 BLOCKED | Aguarda FASE 2 |
| 4 — Temporal Memory | 🔒 BLOCKED | Aguarda FASE 3 |
| 5 — Market Features | 🔒 BLOCKED | Aguarda FASE 4 |
| 6 — Analysis Lab | 🔒 BLOCKED | Aguarda FASE 5 |
| 7 — Outcome Evaluation | 🔒 BLOCKED | Aguarda FASE 6 |
| 8 — Dashboard | 🔒 BLOCKED | Aguarda FASE 7 |

## Como atualizar este arquivo

Ao final de cada fase:

1. registrar o commit/PR de referência;
2. registrar CI e testes relevantes;
3. mudar a fase para `PASS` somente com evidência;
4. desbloquear somente a fase imediatamente seguinte;
5. registrar riscos ou pendências reais;
6. garantir coerência com `ROADMAP.md`, `SCOPE.md` e `DECISIONS.md`.

## Regra de retomada

Se um novo chat/agente não souber onde continuar, a resposta deve ser obtida nesta ordem:

1. `docs/PROJECT_STATE.md`;
2. `docs/ROADMAP.md`;
3. `docs/SCOPE.md`;
4. `docs/DECISIONS.md`;
5. CI/commits/PRs reais do GitHub.

Nunca inferir progresso apenas por conversa anterior.