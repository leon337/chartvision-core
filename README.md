# ChartVision Core

Núcleo experimental para replay, leitura visual de gráficos, reconstrução de candles, memória temporal e avaliação de análises em ambiente controlado.

## Estado atual

**FASE 0 — FOUNDATION: ✅ PASS**

**Próxima fase:** FASE 1 — Replay MVP.

> Antes de trabalhar no projeto, consulte `AGENTS.md` e `docs/PROJECT_STATE.md`. O GitHub é a memória oficial do projeto.

## Documentação oficial

Leitura recomendada:

1. [`AGENTS.md`](AGENTS.md) — regras obrigatórias para Codex/agentes;
2. [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) — ponto exato de retomada;
3. [`docs/SCOPE.md`](docs/SCOPE.md) — escopo congelado e fora do escopo;
4. [`docs/ROADMAP.md`](docs/ROADMAP.md) — fases 0–8 e gates;
5. [`docs/DECISIONS.md`](docs/DECISIONS.md) — decisões arquiteturais aprovadas;
6. [`docs/CONTINUITY_PROTOCOL.md`](docs/CONTINUITY_PROTOCOL.md) — protocolo de memória e handoff;
7. [`docs/CHATGPT_PROJECT_INSTRUCTIONS.md`](docs/CHATGPT_PROJECT_INSTRUCTIONS.md) — cópia canônica da instrução do Projeto ChatGPT;
8. [`docs/architecture.md`](docs/architecture.md) — arquitetura canônica;
9. documentação específica da fase.

## Lifecycle de fase

Cada fase deve iniciar e encerrar por procedimentos padronizados:

- `.agents/skills/chartvision-phase-start/SKILL.md` — valida estado real e produz o Phase Brief;
- `.agents/skills/chartvision-phase-close/SKILL.md` — valida Definition of Done e persiste o handoff.

O desenvolvimento utiliza preferencialmente um chat dedicado por fase.

## Foundation existente

- FastAPI;
- React + TypeScript + Vite;
- PostgreSQL;
- Docker Compose;
- logging estruturado;
- configuração por ambiente;
- health checks;
- testes iniciais;
- CI;
- validação da stack Docker completa;
- contratos arquiteturais para as fases seguintes;
- governança e memória persistentes.

## Escopo do v1

O v1 é um laboratório controlado. Não inclui integração com corretoras, execução de operações, automação de login ou dinheiro real.

O objetivo é provar o ciclo:

```text
Dataset → Replay → Gráfico → Visão → Reconstrução → Memória → Features → Análise → Outcome → Métricas
```

## Executar

```bash
cp .env.example .env
docker compose up --build
```

Serviços:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Health: http://localhost:8000/health

## Testes do backend

```bash
make test
```

## Regra de continuidade

Uma fase somente é concluída com evidência verificável, CI/testes, critérios de aceite, PHASE CLOSE e atualização da documentação de estado. Nenhum agente deve avançar para a fase seguinte apenas porque código foi escrito.
