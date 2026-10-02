# Developer commands. Install `just` (https://just.systems, or
# `uv tool install rust-just`) and run `just` to list them.

set shell := ["bash", "-euo", "pipefail", "-c"]

api_port := env("API_PORT", "8000")
web_port := env("WEB_PORT", "3000")

# List the commands.
default:
    @just --list --unsorted

# Install backend and cabinet dependencies and the git hooks.
setup:
    uv sync --frozen
    cd web && npm ci --no-audit --no-fund
    uvx pre-commit install

# API (worker inside, demo data) and cabinet; demo@example.com, code in the API log.
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    trap 'kill 0' EXIT
    APP_ENV=development SEED_DEMO_DATA=true \
        uv run uvicorn app.main:create_application --factory --reload --port {{api_port}} &
    cd web && BACKEND_URL=http://localhost:{{api_port}} COOKIE_SECURE=false \
        npx next dev --port {{web_port}} &
    wait

# Every check CI runs on the code (backend and cabinet), fastest first.
check: check-backend check-web

# Lint, format, types, then tests with the 95 % coverage floor.
check-backend:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy .
    uv run pyright
    uv run pytest -n auto --cov=app --cov-branch --cov-fail-under=95 --cov-report=term:skip-covered

# Lint, types, tests with coverage floors, generated client, build.
check-web:
    cd web && npm run lint
    cd web && npm run typecheck
    cd web && npm run test:coverage
    cd web && npm run gen:api:types && git diff --exit-code -- src/api/schema.d.ts
    cd web && npm run build

# Format and auto-fix what the linters can.
fix:
    uv run ruff check --fix .
    uv run ruff format .
    cd web && npx eslint --fix .

# Backend tests only (pass pytest arguments: `just test tests/billing -x`).
test *args:
    uv run pytest -n auto {{args}}

# Architecture contracts alone: role layers and dead code.
architecture:
    uv run lint-imports
    uv run vulture

# Regenerate the API description, typed client and generated tables.
gen:
    cd web && npm run gen:api

# Playwright end-to-end suite (builds the cabinet, starts API and cabinet).
e2e:
    cd web && npm run e2e

# Dependency, secret and static-analysis scans (as the CI security job).
security:
    uv export --frozen --no-emit-project --format requirements-txt \
        | uvx pip-audit==2.10.1 --strict --disable-pip --requirement /dev/stdin
    cd web && npm audit --omit=dev --audit-level=high
    uv run bandit -c pyproject.toml -r app scripts -b bandit-baseline.json
    if command -v gitleaks >/dev/null; then gitleaks git --redact --no-banner .; \
        else echo "gitleaks is not installed; skipped (CI runs it)."; fi

# Empty the docker compose data (Postgres, recordings) and migrate again.
db-reset:
    docker compose down --volumes
    docker compose up --detach --wait postgres
    docker compose run --rm migrate

# The whole product in Docker (Postgres, migrations, API, worker, cabinet).
up:
    docker compose up --build
