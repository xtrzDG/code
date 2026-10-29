# Assistant Workshop

An AI front-line assistant for small businesses in any country. It answers a
restaurant's, hotel's, salon's or VR club's customers around the clock, in
their language, on every channel (phone, WhatsApp, Instagram, Messenger,
Telegram, the website chat), books tables, rooms and appointments, takes
requests, and hands anything difficult to a person. The owner fills in a
profile in the cabinet and the assistant builds itself.

Any country works: an owner signs in with a phone number of their own
country (numbers are parsed for 245 regions and stored in E.164), and the
country sets the languages, currency, time zone, emergency number, how
login codes are delivered and the call recording rules. Prices are kept in
the business's currency and bookings are computed in its time zone.

The first market is Italy (the pilot country; plans are priced in EUR). The
owner's cabinet, the public site, the help center, the owner-facing texts
and the legal texts come in English and Italian; the Italian texts are a
team draft awaiting a native speaker's review. The assistant itself speaks
the customers' languages (the website chat alone has 30), whatever the
owner's interface language.

This repository holds the whole product:

- **the backend** (`app/`): a Python 3.14 FastAPI API and a background
  worker on Postgres (EU), typed end to end (mypy and pyright strict, typed
  domain primitives), generated from the
  [`copier-template-python-backend`](https://github.com/eldenizfamilyanskicode/copier-template-python-backend)
  template;
- **the owner's cabinet** (`web/`): Next.js, its own server talking to the
  API ([`web/README.md`](web/README.md));
- **the website widget** (`app/gateways/http/static/widget/`): one script
  without dependencies, served by the API;
- deployment (`Dockerfile`, `docker-compose.yml`, `render.yaml`),
  operations (`ops/`, `docs/operations/`), evaluations (`evals/`) and load
  tests (`perf/`).

## Quick start

You need [uv](https://docs.astral.sh/uv/), Node 22 and
[`just`](https://just.systems) (`uv tool install rust-just`).

```bash
just setup    # backend and cabinet dependencies, the git hooks
just dev      # API on :8000 (worker inside, demo data) and cabinet on :3000
just check    # every check CI runs on the code, fastest first
```

`just dev` needs no database: the data lives in memory and the demo owner
signs in with `demo@example.com` or `+995 555 00 00 01`; the login code is
the newest `Login code NNNNNN via <channel>` line of the API log. Without
model keys the assistant answers with a clear error; export
`LLM_PROVIDER=scripted` for a keyless rehearsal, or `OPENAI_API_KEY` for real
answers ([`docs/dev/environment.md`](docs/dev/environment.md)). Run `just`
to list the other commands (`just test`, `just e2e`, `just gen`,
`just duplication`, `just security`, `just db-reset`, …).

Everything in Docker, with Postgres 16, migrations, the API, the worker and
the cabinet:

```bash
cp .env.example .env            # optional: keys of external services
docker compose up --build       # cabinet http://localhost:3000, API http://localhost:8000
```

## How it is built

The API and the worker are assembled from one composition root
(`app/containers/app.py`) along a fixed role chain: an HTTP route or a
worker job calls an operator, which runs a pipeline, which runs
orchestrators, which run use cases; use cases depend only on contracts
(repositories, registries, facilitators, adapters) and never on each other's
packages. `import-linter` enforces the layers. Tenant data is stored as
JSONB documents in Postgres with row-level security per business; every
write that must reach a customer goes through a transactional outbox.

| Process | Entry point |
| --- | --- |
| HTTP API | `uv run uvicorn app.main:create_application --factory` |
| Background worker | `uv run python -m app.worker_main` |
| Migrations | `uv run python -m app.gateways.cli.migrate` |
| Other operator commands | `app/gateways/cli/` (`workshop backup`, `restore-check`, `migrate-documents`, `backfill-lookup`, …) |

## Where to read next

Developer documentation (English):

| Page | What it covers |
| --- | --- |
| [`docs/dev/running.md`](docs/dev/running.md) | the processes, running locally, the embedded worker, demo data, Docker |
| [`docs/dev/environment.md`](docs/dev/environment.md) | every environment variable and its default, webhook addresses |
| [`docs/dev/api.md`](docs/dev/api.md) | the HTTP API by section, the guided launch and Apply changes, the shared inbox |
| [`docs/dev/widget.md`](docs/dev/widget.md) | the website widget, its limits and live stream, the hosted chat page |
| [`docs/dev/login-codes.md`](docs/dev/login-codes.md) | login code delivery, sign-in protection, two factors, sessions |
| [`docs/dev/operations.md`](docs/dev/operations.md) | health, logs and Sentry, Render, Postgres, backups and keys, periodic jobs |
| [`docs/dev/legal-texts.md`](docs/dev/legal-texts.md) | the DPA, terms, privacy policy and sub-processors in the code |
| [`docs/dev/checks.md`](docs/dev/checks.md) | the checks, the test suites, evaluations and CI |
| [`docs/dev/code-health.md`](docs/dev/code-health.md) | the duplication, dead-code and container-typing ratchets |

Rules and decisions (English):

- [`AGENTS.md`](AGENTS.md): typed domain primitives and their semantic
  identity, the rules every change follows;
- [`docs/conventions.md`](docs/conventions.md): the role chain, files and
  names, stored documents and deploys, time, HTTP, internationalization,
  tests;
- [`docs/adr/`](docs/adr/README.md): the architecture decision records, from
  the document store (0001) to the composition root (0010);
- [`docs/api-versioning.md`](docs/api-versioning.md) and
  [`docs/API_CHANGELOG.md`](docs/API_CHANGELOG.md): the API's compatibility
  rules and its changes;
- [`docs/operations/`](docs/operations/): deploys, CI, capacity, SLOs,
  observability, backups and the runbooks, and the owner's go-live
  checklist ([`go-live.md`](docs/operations/go-live.md));
- [`docs/security/`](docs/security/) and [`SECURITY.md`](SECURITY.md): the
  threat model and how to report a vulnerability;
- [`docs/glossary.md`](docs/glossary.md): the product's terms;
- [`migrations/README.md`](migrations/README.md),
  [`evals/README.md`](evals/README.md), [`web/README.md`](web/README.md).

Product documents (Russian, the owner's working language):

- [`docs/concept.md`](docs/concept.md): the product and its requirements;
- [`docs/architecture.md`](docs/architecture.md): roles, bounded contexts,
  flows and the i18n approach in depth;
- [`docs/PLAN.md`](docs/PLAN.md): the working plan;
- [`docs/LAUNCH.md`](docs/LAUNCH.md): the owner's launch guide (accounts,
  keys, Render, the first check).

## Contributing

Every change keeps `just check` green: ruff, mypy and pyright strict, the
tests with at least 95 % line and branch coverage, the architecture policies
(role layers, no dead code, at most 300 lines per file, document evolution,
the ratchets of [`docs/dev/code-health.md`](docs/dev/code-health.md)) and the
cabinet's lint, types, tests and knip. Business code takes typed primitives
from `app/schemas/typings/`, never raw `str`, `int` or `float`; a stored
shape changes only by expand and contract with an upcaster and a golden
fixture; an API change regenerates `web/openapi.json` (`just gen`) and adds an
entry to `docs/API_CHANGELOG.md`. Pull requests follow
`.github/pull_request_template.md`; `CODEOWNERS` names the reviewers.
