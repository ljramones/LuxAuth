PYTHON ?= python3
TEST_PYTHON := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else command -v $(PYTHON); fi)
RUFF := $(shell if [ -x .venv/bin/ruff ]; then echo .venv/bin/ruff; else command -v ruff; fi)

.PHONY: up down logs ps init test test-unit test-integration lint lint-fix lint-full format smoke clean health generate-synthetic-data ingest-reference-data smoke-real-images reset-local-data seed-dataset-version run-evaluation evaluation-report train-metric-model reembed-reference-data compare-evaluations analyze-embeddings inspect-neighbors calibrate-thresholds export-projection smoke-capture-api generate-lab-capture-batch validate-capture-batch ingest-capture-batch promote-capture-batch smoke-capture-batch ingest-external-dataset ingest-external-dataset-dry-run validate-external-manifest external-dataset-report

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
	$(MAKE) test-unit

test-unit:
	$(TEST_PYTHON) scripts/run_unit_tests.py

test-integration:
	$(MAKE) smoke
	$(MAKE) smoke-capture-api

lint:
	$(RUFF) check .

lint-fix:
	$(RUFF) check . --fix

lint-full:
	$(RUFF) check .

format:
	$(RUFF) format .

smoke:
	$(PYTHON) scripts/run_local_pipeline.py

health:
	@for port in 8101 8102 8103 8104 8106 8201 8202 8203 8204 8205 8301 8302 8303 8401; do \
		printf "%-5s " "$$port"; \
		curl -sf "http://localhost:$$port/health" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('service','?'), '-', d.get('status','?'))" 2>/dev/null || echo "DOWN"; \
	done

generate-synthetic-data:
	$(PYTHON) scripts/generate_synthetic_reference_images.py

ingest-reference-data:
	@test -n "$(DATASET)" || (echo "DATASET=<dataset_version> is required"; exit 2)
	$(PYTHON) scripts/ingest_reference_images.py --dataset $(DATASET) $(if $(DRY_RUN),--dry-run) $(if $(FORCE),--force) $(if $(FORCE_REAL_DATA),--force-real-data)

smoke-real-images:
	python3 scripts/run_real_image_pipeline.py

reset-local-data:
	docker compose down -v && docker compose up -d && sleep 10 && echo "Stack reset complete"

seed-dataset-version:
	@test -n "$(DATASET)" || (echo "DATASET=<dataset_version> is required"; exit 2)
	$(PYTHON) scripts/ingest_reference_images.py --dataset $(DATASET) $(if $(DRY_RUN),--dry-run) $(if $(FORCE),--force) $(if $(FORCE_REAL_DATA),--force-real-data)

run-evaluation:
	python3 scripts/run_evaluation.py $(if $(MODEL),--model $(MODEL))

evaluation-report:
	python3 scripts/print_evaluation_report.py

train-metric-model:
	python3 scripts/train_model.py $(if $(MODEL_VERSION),--model-version $(MODEL_VERSION))

reembed-reference-data:
	@test -n "$(DATASET)" || (echo "DATASET=<dataset_version> is required"; exit 2)
	@test -n "$(MODEL)" || (echo "MODEL=<embedding_model_version> is required"; exit 2)
	$(PYTHON) scripts/reembed_reference_dataset.py --dataset $(DATASET) --model $(MODEL) $(if $(DRY_RUN),--dry-run) $(if $(FORCE),--force)

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
	$(PYTHON) scripts/smoke_capture_api.py

generate-lab-capture-batch:
	python3 scripts/generate_lab_capture_batch.py

validate-capture-batch:
	python3 scripts/validate_capture_batch.py --batch $(BATCH) --auto-create-device

ingest-capture-batch:
	python3 scripts/ingest_capture_batch.py --batch $(BATCH)

promote-capture-batch:
	python3 scripts/promote_capture_batch_to_dataset.py --batch $(BATCH) --dataset $(DATASET)

smoke-capture-batch:
	python3 scripts/smoke_capture_batch.py

ingest-external-dataset:
	$(PYTHON) scripts/ingest_external_dataset.py --manifest $(MANIFEST) $(if $(FORCE),--force)

ingest-external-dataset-dry-run:
	$(PYTHON) scripts/ingest_external_dataset.py --manifest $(MANIFEST) --dry-run

validate-external-manifest:
	$(PYTHON) scripts/validate_external_manifest.py --manifest $(MANIFEST)

external-dataset-report:
	@test -n "$(DATASET)" || (echo "Usage: make external-dataset-report DATASET=<version> MODEL=<version>"; exit 2)
	@test -n "$(MODEL)" || (echo "Usage: make external-dataset-report DATASET=<version> MODEL=<version>"; exit 2)
	$(PYTHON) scripts/external_dataset_report.py --dataset $(DATASET) --model $(MODEL) --overwrite

clean:
	docker compose down -v --rmi local
