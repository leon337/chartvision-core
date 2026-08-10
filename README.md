# ChartVision Core

Núcleo experimental para replay, leitura visual de gráficos, reconstrução de candles e avaliação de análises em ambiente controlado.

## Escopo atual

Este repositório contém apenas a **FASE 0 — FOUNDATION**:

- FastAPI
- React + TypeScript + Vite
- PostgreSQL
- Docker Compose
- logging estruturado
- configuração por ambiente
- health checks
- testes iniciais
- CI
- estrutura arquitetural para as fases seguintes

Não contém integração com corretoras, execução de operações ou automação de trading.

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

## Próxima fase

FASE 1 — ReplaySource + ChartRenderer determinísticos.
