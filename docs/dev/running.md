# Running the backend

How the backend is built, started and fed with demo data on a developer's
machine. The owner's step-by-step launch (accounts, keys, Render, the first
check) is the Russian [`docs/LAUNCH.md`](../LAUNCH.md); every environment
variable is in [`environment.md`](environment.md).

## The processes

| Process | Entry point | What it does |
| --- | --- | --- |
| HTTP API | `app.main:create_application` (a uvicorn factory) | the cabinet, the catalog, channel, voice and payment webhooks, the website widget |
| Background worker | `python -m app.worker_main` | periodic jobs and the job queue in lanes (answers to inbound messages, outbound deliveries, autotests of assistant versions and more); any number of workers; in development without Postgres it runs as a thread inside the API (`EMBEDDED_WORKER`) |
| Migrations | `python -m app.gateways.cli.migrate` | the Postgres schema (EU) with row-level security per business; never blocks writes during a deploy: a lock wait of at most 5 s, retries, indexes built `CONCURRENTLY` ([`migrations/README.md`](../../migrations/README.md)) |
| Document migration | `python -m app.gateways.cli.migrate_documents` | rewrites stored documents of older schema versions to the current one (after a deploy, [`docs/operations/deploys.md`](../operations/deploys.md)) |
| Lookup backfill | `python -m app.gateways.cli.backfill_lookup` | fills new lookup columns of rows written before their migration, in batches (after a deploy, [`docs/operations/deploys.md`](../operations/deploys.md)) |
| Audit log purge | `python -m app.gateways.cli.purge_audit_log` | deletes audit entries older than `--older-than-days` (at least 365) from each hash chain in batches and leaves a checkpoint, so the chain still verifies; run by an operator, not as a `preDeployCommand` ([runbook](../operations/runbooks/audit-chain-broken.md)) |
| Load data | `python -m app.gateways.cli.seed_load` | fills a database for load tests (500 businesses, 2 million messages, 200,000 bookings) and writes a manifest for k6; never in production ([`docs/operations/capacity.md`](../operations/capacity.md)) |

All of them ship in one image (`Dockerfile`, roles `api`, `worker`,
`migrate`, `migrate-documents`, `backfill-lookup`, `purge-audit-log`,
`seed-load`); the owner's cabinet (Next.js) is a separate image,
`web/Dockerfile`, described in [`web/README.md`](../../web/README.md).

The API and the worker are assembled from one composition root,
`app/containers/app.py::AppContainer` (dependency-injector, see
[ADR 0010](../adr/0010-composition-root.md)): clients → adapters →
repositories, registries, facilitators, transformers, utilities → use cases
→ orchestrators → pipelines → operators. `app/gateways/http/router_assembly.py`
assembles the routers of every section.

## Starting locally

`just dev` starts the API (with the worker inside and demo data) and the
cabinet. By hand:

```bash
uv sync
cp .env.example .env            # fill in the keys you need

# API (http://127.0.0.1:8000/docs is the OpenAPI description)
uv run uvicorn app.main:create_application --factory --reload

# background worker (on SIGINT/SIGTERM it gives running jobs up to 25 s);
# a separate process with Postgres; without DATABASE_URL it runs in the API
uv run python -m app.worker_main
```

Without `DATABASE_URL` the data lives in the process's memory (handy for
demos and tests). A separate worker could not see the API's data then, so in
development (`APP_ENV=development`) without `DATABASE_URL` the API runs the
worker in a thread of its own: autotests of versions finish, reminders go
out, and no second process is needed. That is `EMBEDDED_WORKER`:

| Value | What it does |
| --- | --- |
| `auto` (default) | the worker runs inside the API only with `APP_ENV=development` and an empty `DATABASE_URL` |
| `true` | always inside the API (for example development against a local Postgres without a separate worker); refused in production, where workers are their own service (`workshop worker`) so autotests never slow the API down |
| `false` | never; run `python -m app.worker_main` |

There may be several workers (processes, service instances, an embedded one
next to a separate one, all on one Postgres): a job is taken from the queue
with a lease (`FOR UPDATE SKIP LOCKED`), the worker extends the lease while
the job runs, and another worker picks up a crashed worker's job once its
lease ends. Each lane (`inbound`, `outbound`, `default`, `autotests`, `ops`)
has its own threads (`WORKER_LANE_CONCURRENCY`), so a long autotest run never
delays reminders or answers to customers; one business's autotests run one at
a time. Each sending provider (Meta, Telegram, the platform bot, Twilio, SMTP,
Flitt) has its own circuit breaker, and one provider takes at most half of the
`outbound` threads: a hanging provider does not hold up the others, and the
platform's alerts go in their own `ops` lane
(`docs/operations/runbooks/provider-circuits.md`). Periodic jobs run in a thread of their own and once per period (a day,
an ISO week or an interval) across all workers, recorded in
`periodic_job_runs`, so a restart does not repeat today's reminders and
digests. Finished jobs are kept for 30 days; a platform admin sees dead ones
and retries them with `GET /v1/admin/jobs?status=dead` and
`POST /v1/admin/jobs/{job_id}/retry` (or `…/discard`), with an audit entry.

The application starts with an empty environment too: without keys, an
external service answers with a clear error (HTTP 502) instead of breaking
the start.

At start-up the API warms the country catalog, registers the platform bot's
Telegram webhook (when `TELEGRAM_PLATFORM_BOT_TOKEN`, `ENCRYPTION_KEY` and
`APP_BASE_URL` are set), creates the demo businesses with
`SEED_DEMO_DATA=true`, sends the model call log to Langfuse once a minute
and starts the embedded worker when `EMBEDDED_WORKER` says so; on shutdown
it stops the worker, flushes the log and closes the Postgres pool. Behind a
proxy run uvicorn with `--proxy-headers --forwarded-allow-ips=<proxy
address>`: the client's IP goes into the audit log.

## Demo data

To make an empty installation look like a live product (for showing it and
for screenshots), start the API with `SEED_DEMO_DATA=true`:

```bash
APP_ENV=development SEED_DEMO_DATA=true uv run uvicorn app.main:create_application --factory
```

Once at start-up (a restart duplicates nothing, in memory or in Postgres)
the API creates a demo owner (`+995 555 00 00 01`, `demo@example.com`) and
a staff member (`+995 555 00 00 02`), and two businesses of the owner:

- the restaurant "Mtsvane Ezo" in Tbilisi (Georgia, lari; guests write in
  Georgian, Russian, English, Hebrew and Arabic): a filled profile, a menu
  with prices, tables, hours and special days, a published assistant version
  that passed its autotests, Telegram, WhatsApp, the website chat and the
  phone, about 40 conversations in a month with tool calls, a call with a
  transcript, bookings (upcoming, past, no-shows, cancelled), leads,
  handoffs to staff, unanswered questions, a trial and a package about 80 %
  used;
- the beauty salon "Studio Lindenblatt" in Berlin (Germany, euro, German and
  English): services, staff, bookings and a few conversations.

In development the login code is written to the API log (see
[`login-codes.md`](login-codes.md)). To enter the admin area as well, add
`PLATFORM_ADMIN_PHONE_NUMBERS=+995555000001`. The channel credentials are
made up; seeding calls no provider. The variable is refused in
`production`: the API does not start.

## Everything in Docker

```bash
cp .env.example .env            # optional: keys of external services
docker compose up --build       # cabinet http://localhost:3000, API http://localhost:8000
```

`docker-compose.yml` starts Postgres 16, one-off migrations (`migrate`), the
API, the worker and the cabinet (`web`, `BACKEND_URL=http://api:8000`,
`COOKIE_SECURE=false` for http). It sets `APP_ENV=development`, so without a
configured provider login codes appear in the API log:
`docker compose logs -f api`. The application connects as the role
`workshop` without superuser rights (created by `docker/postgres/init`), so
row-level security works locally too. The API and the worker encrypt channel
tokens with one `ENCRYPTION_KEY`; the default in `docker-compose.yml` is
public and fit for this machine only. Before connecting real channels set
your own in `.env` (for example `python -c "import secrets;
print(secrets.token_urlsafe(32))"`) and never change it afterwards; with
`APP_ENV=production` the API refuses the default. `API_PORT` and `WEB_PORT`
change the ports (`APP_BASE_URL` and `CABINET_BASE_URL` follow them).
Sign-ins through the local cabinet all come from the container's one
address, so Compose raises the per-address code limit to 100 an hour.
`docker compose down -v` deletes the data as well. A step-by-step guide with
a sign-in that needs no SMS is in [`docs/LAUNCH.md`](../LAUNCH.md).

The backend image alone:

```bash
docker build -t assistant-workshop-backend .
docker run --env-file .env -p 8000:8000 assistant-workshop-backend api
docker run --env-file .env assistant-workshop-backend worker
docker run --env-file .env assistant-workshop-backend migrate --dry-run
```

The image runs as an unprivileged user, defaults to `APP_ENV=production`
(which needs `ENCRYPTION_KEY`), listens on `$PORT` (8000), answers the
liveness check at `GET /healthz` and the readiness check at `GET /readyz`
([`operations.md`](operations.md)). The API starts with `--proxy-headers`;
the trusted proxies' addresses go to `FORWARDED_ALLOW_IPS` (127.0.0.1 by
default). Give the proxies' address ranges, never `*`: with `*` uvicorn takes
the leftmost `X-Forwarded-For` address, which the client writes itself, and
the IP in the audit log could be forged.
