.PHONY: backend-up backend-stop backend-health workbench dev check test lint notebook-deps notebook-kernel notebook

backend-up:
	./scripts/start-backend.sh

backend-stop:
	./scripts/stop-backend.sh

backend-health:
	cd auth-platform && make health

workbench:
	./scripts/start-workbench.sh

dev:
	./scripts/start-dev.sh

check:
	./scripts/check-local-stack.sh

test:
	cd auth-platform && make test

lint:
	cd auth-platform && make lint-full
	cd capture-workbench && npm run build

notebook-deps:
	cd auth-platform && .venv/bin/python -m pip install -r ../notebooks/requirements.txt

notebook-kernel:
	cd auth-platform && .venv/bin/python -m ipykernel install --user --name luxauth-auth-platform --display-name "LuxAuth auth-platform"

notebook:
	cd auth-platform && .venv/bin/jupyter lab --notebook-dir=../notebooks
