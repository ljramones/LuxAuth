.PHONY: backend-up backend-stop backend-health workbench dev check test lint

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
