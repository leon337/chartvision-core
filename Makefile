.PHONY: up down build logs test lint format backend-shell

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

test:
	docker compose run --rm backend pytest -q

lint:
	docker compose run --rm backend ruff check app

format:
	docker compose run --rm backend ruff format app

backend-shell:
	docker compose run --rm backend sh
