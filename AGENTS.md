# Repository Guidelines

## Project Structure & Module Organization

This repository is a private monorepo for luxury-goods authentication. The active code lives in `auth-platform/`, which contains FastAPI microservices in `services/`, shared Python code in `libs/auth_common/`, ML training code in `ml/`, local infrastructure in `infra/`, utility scripts in `scripts/`, and test/sample fixtures in `sample_data/`. Repo-level documentation lives in `docs/`. `iphone-app/` and `android-app/` are reserved for future capture clients and currently contain only scaffolding.

## Build, Test, and Development Commands

Run backend work from `auth-platform/`.

- `make up`: build and start the full Docker Compose stack.
- `make down`: stop the stack and remove volumes.
- `make health`: check service health endpoints on local ports.
- `make test`: run `pytest` across services and shared libs.
- `make lint`: run `ruff check .`.
- `make format`: apply `ruff format .`.
- `make smoke`: run the local end-to-end pipeline smoke test.

Typical setup:

```bash
cd auth-platform
cp .env.example .env
make up
make smoke
```

## Coding Style & Naming Conventions

Target Python is 3.12. Use 4-space indentation, keep lines within Ruff’s 120-character limit, and prefer explicit, typed FastAPI/Pydantic code. Follow existing layout: each service keeps app code in `app/` and tests in `tests/`. Use `snake_case` for modules, functions, and scripts; `PascalCase` for classes; and descriptive service names such as `region-scoring-service`.

## Testing Guidelines

Tests use `pytest` with `pytest-asyncio`. Name files `test_*.py` and test functions `test_*`. Keep unit tests next to the service or library they cover, for example `services/decision-service/tests/test_decision_logic.py`. Run `make test` before opening a PR; run `make smoke` for changes that affect the event pipeline, scripts, or Docker wiring.

## Commit & Pull Request Guidelines

Recent commits use short, imperative subjects such as `Add device-agnostic capture intake service`. Follow that pattern and keep the first line specific. PRs should include a concise description, affected areas (`services/`, `libs/`, `ml/`, `docs/`), validation performed (`make test`, `make smoke`, manual API checks), and screenshots only when UI work exists.

## Security & Configuration Tips

Do not commit secrets, production data, or private customer assets. Keep credentials in local `.env` files, which are gitignored. Treat `sample_data/` and docs as safe development artifacts only, and review `docs/security-and-secrets.md` before adding new configuration or external integrations.
