# Operating the backend

Health, time limits, logs and error reports; the Render deployment; Postgres;
backups and key rotation; the periodic jobs. The runbooks, SLOs and capacity
figures are in [`docs/operations/`](../operations/); the owner's launch guide
is the Russian [`docs/LAUNCH.md`](../LAUNCH.md).

## Observability and resilience

- **Health.** `GET /healthz` is asynchronous and touches neither threads nor
  the database, so it answers even when all `THREADPOOL_SIZE` request
  threads are busy. `GET /readyz` (Render routes traffic by it) runs
  `select 1` with a 2 s timeout and checks that every migration of this
  build is applied; otherwise 503. A busy connection pool is not a refusal:
  the answer stays `ready` (200) with the pool check `degraded`, and turns
  503 only after the pool has been busy for 30 s in a row. The age of the
  worker's last heartbeat (`worker_heartbeats`, migration 1030; the worker
  writes it every tick with its version and the outcome of the periodic
  jobs) is in the answer but never stops traffic.
- **Time limits.** Every Postgres connection has `statement_timeout=10s` and
  `idle_in_transaction_session_timeout=30s` (30 min and 5 min for
  `workshop migrate`). A model call in a chat has
  `LLM_CALL_TIMEOUT_SECONDS` (25 s) and one retry; a voice agent's tool
  answers within 8 s (otherwise the agent gets an error and tells the
  caller a colleague will call back).
- **Shutdown.** uvicorn gives open requests 25 s
  (`--timeout-graceful-shutdown 25`, keep-alive 5 s), the worker gives
  running jobs 25 s; Render waits 30 s and 60 s
  (`maxShutdownDelaySeconds`).
- **Logs.** `LOG_FORMAT=json` (the default in `production`): one JSON line
  per record with the time, level, logger, thread, text and `request_id`,
  `business_id`, `conversation_id`, `channel`, `job_name`, `job_id`; the
  same `X-Request-ID` is returned in the response. Bot tokens in URLs are
  masked.
- **Sentry.** `SENTRY_DSN`: errors of the API and the worker with the build's
  version (`RENDER_GIT_COMMIT`/`APP_RELEASE`) and context tags, the share of
  traces `SENTRY_TRACES_SAMPLE_RATE`, Sentry Crons check-ins around every
  periodic job (a missed or failed run shows in Sentry), errors of the
  website widget (`POST /v1/widget/errors`) and of the cabinet (the
  `SENTRY_DSN` of the `workshop-cabinet` service, `web/README.md`). No
  request bodies, users or breadcrumbs. CI uploads the cabinet's source maps
  on commits to `main` when GitHub has the secret `SENTRY_AUTH_TOKEN` and the
  variables `SENTRY_ORG` and `SENTRY_PROJECT`
  ([`docs/operations/observability.md`](../operations/observability.md),
  which also covers the Prometheus metrics and OpenTelemetry traces).

## Deploying to Render (EU)

`render.yaml` is a Blueprint: in Render choose **New → Blueprint** and pick
the repository (step by step, with the list of keys and webhook addresses, in
[`docs/LAUNCH.md`](../LAUNCH.md)). Everything is created in Frankfurt:

| Resource | What it is |
| --- | --- |
| `workshop-db` | managed Postgres 16, reachable only from inside Render |
| `workshop-api` | the API from `Dockerfile`; `workshop migrate` before every deploy, readiness at `/readyz`, 30 s for requests to finish on shutdown |
| `workshop-worker` | the background worker from the same image; 60 s for jobs to finish on shutdown |
| `workshop-backup` | the nightly backup (a cron service from the same image): `workshop backup` |
| `workshop-cabinet` | the cabinet from `web/Dockerfile` |

On creation Render asks for the secrets (`sync: false`): the model provider
and its keys, the login code providers, Meta (and the WhatsApp templates),
Telegram, ElevenLabs, Flitt, Langfuse, Sentry; leave the ones you do not need
empty. The worker gets from the API only the keys `render.yaml` names for
it; set every other variable (model tuning, `OPENAI_BASE_URL`,
`LANGFUSE_HOST`, `RECORDING_RETENTION_DAYS`, `WORKER_POLL_SECONDS` and the
like) in the environment group `workshop-backend`, which both the API and
the worker read. `ENCRYPTION_KEY` is generated once (never replace it in
place: keys rotate through `ENCRYPTION_KEYS`, see below). After the first
deploy set `APP_BASE_URL` (the API's public address, for example
`https://workshop-api.onrender.com`), `CABINET_BASE_URL` (the cabinet's
public address, for example `https://workshop-cabinet.onrender.com`, where
Google Calendar and the payment page send the owner back),
`CORS_ALLOWED_ORIGINS` of the API (the cabinet's address again) and the
cabinet's `BACKEND_URL` (the API's internal Render address,
`http://<host>:8000`; never the public one, or every sign-in would come from
one Render address and hit the per-address code limit). The webhook
addresses for the providers' dashboards are in
[`environment.md`](environment.md).

Deploys happen only after the checks: the services of `render.yaml` follow
the `release` branch and deploy a commit only when every GitHub check on it
is green (`autoDeployTrigger: checksPass`). `render.staging.yaml` is the same
environment as staging on `main`, with its own database and the group
`workshop-staging` (`LLM_PROVIDER=scripted`: a rehearsal without a model).
After every deploy `.github/workflows/deploy-smoke.yml` runs
`scripts/smoke.sh`; a green staging moves the commit to `release`. The rules
for schema changes (expand first, contract later), the document migration
and rollbacks are in [`docs/operations/deploys.md`](../operations/deploys.md)
and [ADR 0007](../adr/0007-online-safe-migrations.md).

## Postgres (EU)

```bash
export DATABASE_URL=postgresql://app_user:...@host:5432/workshop?sslmode=require
uv run python -m app.gateways.cli.migrate --dry-run   # what would be applied
uv run python -m app.gateways.cli.migrate             # apply
```

The migrations of `migrations/` are applied in order, each in its own
transaction; running them on every deploy and from several instances at once
is safe. The API, the worker and the migrations must connect with a role
that is neither a superuser nor `BYPASSRLS`, or Postgres skips the isolation
policies. Details in [`migrations/README.md`](../../migrations/README.md).

## Backups and keys

```bash
workshop backup          # database snapshot → age → an EU bucket; kept 30 days + 12 months
workshop restore-check   # restore a fresh copy into a scratch database and check it
```

Render keeps its own snapshots and point-in-time recovery; on top of that
the cron service `workshop-backup` takes a `pg_dump` of one consistent
snapshot every night, encrypts it in the age format with the public keys of
`BACKUP_AGE_PUBLIC_KEY` (no private key is on the servers) and stores it in
another provider's EU bucket (`BACKUP_S3_*`) with a manifest: the rows of
every table, the migrations, the tables under row-level security. Restore
drills (`.github/workflows/restore-drill.yml`): every night a backup →
restore round on the current code, every Monday a fresh production copy into
a scratch database; rows, migrations and business isolation are checked and
reported to Sentry Crons. To rotate the encryption key put the new key first
in `ENCRYPTION_KEYS`, then a platform admin starts the re-encryption (cabinet
→ Encryption keys, or `POST /v1/admin/security/encryption-keys/rotate`). RPO,
RTO, key custody and the step-by-step restore are in
[`docs/operations/backup-restore.md`](../operations/backup-restore.md).

## Periodic jobs

The main ones (`app/gateways/worker/periodic/` has them all):

| Job | Interval | What it does |
| --- | --- | --- |
| `purge_expired_recordings` | daily | deletes call recordings and transcripts older than the business's retention |
| `end_trials` | hourly | ends trials (unpaid ones go into a grace period) |
| `enforce_grace_periods` | hourly, after `end_trials` | switches to leads-only mode when the grace period ends |
| `check_package_usage` | daily | warns the owner at 80 % of the package's minutes and conversations |
| `send_booking_reminders` | every 15 minutes | reminds customers of bookings in the next 24 hours |
| `purge_finished_jobs` | daily | deletes done, dead and discarded queue jobs and periodic run records older than 30 days |
| `flush_llm_traces` | every minute | sends the model call log to Langfuse (in every worker process) |
| `purge_stale_rows` | daily | deletes expired sessions, login codes older than a day and webhook receipts older than 30 days |
| `rotate_encrypted_secrets` | when an admin starts it | re-encrypts channel and calendar tokens with the current key and registers the Telegram webhooks again |
