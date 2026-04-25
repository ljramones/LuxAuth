.PHONY: up down logs ps init test lint format smoke clean

up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f

ps:
	docker compose ps

init:
	docker compose up -d postgres localstack && sleep 5 && echo "Infrastructure ready"

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

smoke:
	python scripts/run_local_pipeline.py

clean:
	docker compose down -v --rmi local
