.PHONY: up down logs ps init test lint format smoke clean health generate-synthetic-data ingest-reference-data smoke-real-images reset-local-data seed-dataset-version run-evaluation evaluation-report train-metric-model reembed-reference-data compare-evaluations analyze-embeddings inspect-neighbors calibrate-thresholds export-projection smoke-capture-api

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
	python3 scripts/run_local_pipeline.py

health:
	@for port in 8101 8102 8103 8104 8106 8201 8202 8203 8204 8205 8301 8302 8303; do \
		printf "%-5s " "$$port"; \
		curl -sf "http://localhost:$$port/health" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('service','?'), '-', d.get('status','?'))" 2>/dev/null || echo "DOWN"; \
	done

generate-synthetic-data:
	python3 scripts/generate_synthetic_reference_images.py

ingest-reference-data:
	python3 scripts/ingest_reference_images.py

smoke-real-images:
	python3 scripts/run_real_image_pipeline.py

reset-local-data:
	docker compose down -v && docker compose up -d && sleep 10 && echo "Stack reset complete"

seed-dataset-version:
	python3 scripts/ingest_reference_images.py

run-evaluation:
	python3 scripts/run_evaluation.py $(if $(MODEL),--model $(MODEL))

evaluation-report:
	python3 scripts/print_evaluation_report.py

train-metric-model:
	python3 scripts/train_model.py $(if $(MODEL_VERSION),--model-version $(MODEL_VERSION))

reembed-reference-data:
	python3 scripts/reembed_reference_dataset.py --model $(or $(MODEL),texture_baseline_v0.1.0)

compare-evaluations:
	python3 scripts/compare_evaluations.py $(if $(MODELS),--models $(MODELS))

analyze-embeddings:
	python3 scripts/analyze_embeddings.py --model $(or $(MODEL),texture_baseline_v0.1.0)

inspect-neighbors:
	python3 scripts/inspect_neighbors.py --model $(or $(MODEL),texture_baseline_v0.1.0) --output reports/neighbors

calibrate-thresholds:
	python3 scripts/calibrate_thresholds.py --model $(or $(MODEL),texture_baseline_v0.1.0)

export-projection:
	python3 scripts/export_embedding_projection.py --model $(or $(MODEL),texture_baseline_v0.1.0)

smoke-capture-api:
	python3 scripts/smoke_capture_api.py

clean:
	docker compose down -v --rmi local
