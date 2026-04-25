.PHONY: up down logs ps init test lint format smoke clean health generate-synthetic-data ingest-reference-data smoke-real-images reset-local-data

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

health:
	@for port in 8101 8102 8103 8104 8201 8202 8203 8204 8205 8301 8302 8303; do \
		printf "%-5s " "$$port"; \
		curl -sf "http://localhost:$$port/health" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('service','?'), '-', d.get('status','?'))" 2>/dev/null || echo "DOWN"; \
	done

generate-synthetic-data:
	python scripts/generate_synthetic_reference_images.py

ingest-reference-data:
	python scripts/ingest_reference_images.py

smoke-real-images:
	python scripts/run_real_image_pipeline.py

reset-local-data:
	docker compose down -v && docker compose up -d && sleep 10 && echo "Stack reset complete"

clean:
	docker compose down -v --rmi local
