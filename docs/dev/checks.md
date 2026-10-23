# Checks, tests and CI

`just check` runs every check CI runs on the code of the backend and the
cabinet, the duplication ratchet (`just duplication`) included;
[`code-health.md`](code-health.md) describes the ratchets that keep
duplication, dead code and untyped wiring from growing.

## Locally

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pyright
uv run pytest
```

Shorter, with [`just`](https://just.systems) (`justfile`): `just setup`
(dependencies and the git hook of `.pre-commit-config.yaml`), `just dev` (the
API with demo data and the cabinet), `just check` (everything CI checks in
the backend's and the cabinet's code), `just gen`, `just e2e`,
`just duplication`, `just security`, `just db-reset`. pytest includes the
architecture policies of `tests/architecture_policy/` (role layers, dead code,
the 300-line limit, document evolution, the container ignore ratchet and
more) and the platform checks of `tests/platform/` (API contract, CI
workflows, environment variables, these docs).

## Performance and answer quality

A separate suite, `uv run pytest -m perf tests/perf`, checks the latency
budgets (p95 of sign-in, the conversation list, the card, free times, the
dashboard and the widget's polling) on a large database
(`PERF_SCALE=small|medium|full`; plain `pytest` excludes it); once a week
`.github/workflows/perf.yml` runs it and the k6 scenarios, details in
[`docs/operations/capacity.md`](../operations/capacity.md).

The evaluation harness (`evals/`) measures the assistant's answers: 454
scenarios of 16 niches (ka, ru, en, and he and ar for four niches). Every
`pytest` run (`tests/evals`) replays them offline from recorded model
answers (`evals/cassettes`); a changed prompt or tool marks a recording stale
with a reason, and `uv run python -m scripts.run_evals --record
--update-baseline` records it again. Every night
`.github/workflows/evals-nightly.yml` plays them on live models (pass^3, a
judge of another model family) and compares them with `evals/baselines`;
details in [`evals/README.md`](../../evals/README.md) and
[ADR 0008](../adr/0008-offline-replay-evals.md).

## Quality gates in CI

At least 95 % line and branch coverage of `app/`
(`pytest -n auto --cov=app --cov-branch`), the coverage floors of the
cabinet's `src/lib` and `_lib` (`npm run test:coverage`), the role layers
(`.importlinter`, [ADR 0002](../adr/0002-role-chain-and-layers.md)), dead
code (`vulture`, knip), the duplication ratchet (jscpd), current
`openapi.json` and `schema.d.ts`, API compatibility inside `/v1` (`oasdiff`,
[`docs/api-versioning.md`](../api-versioning.md),
[`docs/API_CHANGELOG.md`](../API_CHANGELOG.md)) and the security checks
(pip-audit, npm audit, gitleaks, bandit, CodeQL, Trivy, SBOM; Dependabot
weekly), see [`SECURITY.md`](../../SECURITY.md).

CI (`.github/workflows/ci.yml`) runs the backend checks (with Postgres 16 from
Ubuntu's packages), the cabinet's linter, type check, tests and build
(`web/`), the security checks, builds both Docker images, scans them with
Trivy and validates `docker-compose.yml`. The backend tests run in parallel
parts: the Postgres ones (the `postgres` marker set by `tests/conftest.py`) in
two, the rest in four; files are split by measured duration
(`tests/durations.json`, `TEST_PART=k/n`), `coverage combine` adds up every
part's coverage, and the 95 % floor is checked on the sum. The cabinet builds
in a job of its own next to its checks; after the build the `e2e` job runs
the Playwright browser tests (`web/e2e/`) in shards split by the specs'
measured duration (`web/e2e/durations.json`): each starts the built `.next`
and its own API in development mode (in memory, demo data). How CI is laid
out, the jobs' expected times and how to refresh both duration files are in
[`docs/operations/ci.md`](../operations/ci.md). The suite covers sign-in by
phone and e-mail, creating a business, the profile, every section, switching
language and the widget demo (`cd web && npm run e2e`, see `web/README.md`). A
test that passed only on a retry goes to the summary and
`web/e2e/flaky.json`; on `main` a new such test fails the job. The last job
writes every job's duration to the summary and warns about jobs over 8
minutes. Grouped patch and minor Dependabot updates merge themselves after a
green CI (`.github/workflows/automerge.yml`); Dependabot does not propose
majors of typescript, eslint and @types/node, which are reviewed quarterly
from the issue of `.github/workflows/major-updates.yml`. The property tests
(Hypothesis, `tests/properties/`) are reproducible;
`HYPOTHESIS_PROFILE=explore` searches deeper.

## How the tests are built

The end-to-end tests (`tests/e2e/`) assemble the real `AppContainer` and
replace only the edges: the settings, the clock, the model
(`ScriptedLlmAdapter`), code delivery and external HTTP services
(`httpx.MockTransport`). The storage tests start a local Postgres 16 when it
is installed (`POSTGRES_BIN_DIRECTORY`) and are skipped without it. Unit tests
use in-memory repositories and fakes that implement the contracts; no test
reaches the network, and concurrency is proven with locks and barriers, never
with sleeps or retries ([`docs/conventions.md`](../conventions.md)).
