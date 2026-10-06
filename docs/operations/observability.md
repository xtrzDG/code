# Metrics, traces and logs

How the platform shows what it is doing: Prometheus metrics for graphs and
alerts, OpenTelemetry traces to follow one customer message from its
webhook to the reply, and log lines that carry the same ids. The service
levels these feed are in `docs/operations/slo.md`; the dashboards are in
`ops/grafana/`.

Everything here is off until it is configured, and nothing here carries
personal data: labels and span attributes hold route templates, channels,
lanes, providers, models, job names, tables and status codes, never ids of
people, texts, phone numbers, URLs with queries or statement parameters.

## Metrics (Prometheus)

| Where | How to read it |
| --- | --- |
| API | `GET /metrics` with `Authorization: Bearer <METRICS_TOKEN>`; 401 without the token, 404 while `METRICS_TOKEN` is not set |
| Worker | `http://<worker>:<WORKER_METRICS_PORT>/metrics` with the same token (needs both variables) |

Several uvicorn processes in one API instance (`WEB_CONCURRENCY` > 1) keep
their series in files under `PROMETHEUS_MULTIPROC_DIR` (`workshop api`
sets it and empties it at start), and `/metrics` adds them up; gauges then
take the sum (connections in use) or the worst value (circuit state) of
the processes alive.

The series:

| Series | Labels | What it shows |
| --- | --- | --- |
| `workshop_http_request_duration_seconds` | `method`, `route` (template), `status_class` | every answered request and its time; the 5xx share is the availability SLI |
| `workshop_rate_limit_rejections_total` | `route` | requests refused with 429 |
| `workshop_webhook_messages_total` | `channel`, `outcome` (`received`, `queued`, `duplicate`) | customer messages the webhooks brought |
| `workshop_job_pickup_delay_seconds` | `lane` | how long due jobs waited for a worker |
| `workshop_queue_due_jobs`, `workshop_queue_oldest_wait_seconds` | `lane` | the queue right now (read from the database at scrape time, the same on every instance) |
| `workshop_dead_jobs` | `job` | dead letters now; `workshop_jobs_died_total` counts the deaths |
| `workshop_answer_latency_seconds` | `channel` | from a customer's first unanswered message to the stored reply |
| `workshop_outbound_attempts_total` | `provider`, `outcome` (`delivered`, `retry`, `dead`) | outbox sends; failures by provider |
| `workshop_llm_call_duration_seconds` | `provider`, `model`, `outcome` (`ok`, `error`, `refused`) | model calls and their time |
| `workshop_llm_tokens_total` | `provider`, `model`, `direction` | tokens of successful calls |
| `workshop_db_pool_connections_in_use`, `workshop_db_pool_wait_seconds` | | pool saturation and the waits for a connection |
| `workshop_circuit_breaker_state` | `circuit` | 0 closed, 1 half-open, 2 open |

The API also reports its process (CPU, memory, file descriptors) when it
runs one uvicorn process.

**On Render.** The API's `/metrics` is public behind the token. Render's
background workers accept no inbound traffic, so their port is reachable
only when the worker runs as a private service or next to an agent; the
queue series are on the API's `/metrics` too, so the queue can always be
graphed. Scrape with Grafana Alloy or Prometheus (EU region) every 15-30 s.

**Dashboards.** `ops/grafana/workshop-service.json` graphs every series
above in one dashboard (HTTP, webhooks and the queue, answers and models,
outbound sends, the database pool and the circuit breakers) and the burn
rates of both error budgets; `ops/grafana/README.md` says how to import it.

## Service level rows (`record_sli`)

The SLOs of `docs/operations/slo.md` are counted in the database rather
than in Prometheus, so every instance, the error budget card and the
alerts read the same figures (migration 1163):

- Each API process counts the requests it answers (not `/healthz`,
  `/readyz` or `/metrics`) and those answered with a 5xx, per five-minute
  slot, and adds them to `service_level_slots` every 15 s and at shutdown;
  a failed write keeps the counts for the next one.
- The `record_sli` job (every 5 min, once across workers) judges the
  customer messages of each slot once the 60 s deadline has passed: a
  message answered or handed off within 60 s of arriving is good. After
  each full hour it writes a `service_level_hours` row: messages and those
  in time, the reply p95 from `messages.reply_latency_ms`, API requests and
  server errors. A first run starts with the previous hour; a stopped job
  catches up at most one day.
- Slots are kept 35 days, hour rows 90 days.
- `/admin/system` shows the error budget of the last 28 days per objective
  and the last hour's burn rate (`GET /v1/admin/system/error-budget`), and
  the four burn-rate alerts read the slots.

## Traces (OpenTelemetry and Sentry)

With `OTEL_EXPORTER_OTLP_ENDPOINT` (an OTLP/HTTP collector, EU region;
`OTEL_EXPORTER_OTLP_HEADERS` carries its key) every process sends spans:

- each HTTP request (`GET /v1/businesses/{business_id}/bookings`), which
  continues the caller's trace when it sent a `traceparent`;
- each queued job (`job process_inbound_message`), which continues the
  trace of the request or job that queued it;
- each database statement (`SELECT conversations`: the operation and the
  table, never the parameters or the text);
- each call to a provider's HTTP API (method and host) and each model call
  (provider, model, tokens).

`OTEL_TRACES_SAMPLE_RATE` (0.1) is the share of traces started here that
are kept; a trace continued from elsewhere keeps its decision.
`OTEL_SERVICE_NAME` names the process (`workshop-api` or
`workshop-worker` by default).

Sentry keeps its own sampled performance traces (`SENTRY_TRACES_SAMPLE_RATE`)
and now records the database statements and outgoing HTTP calls inside
them the same way. Trace headers are never sent to providers.

## One id from the webhook to the reply

The request id (`X-Request-ID`) and the trace id travel together:

1. The webhook's request binds both; every log line of the request has
   `request_id` and `trace_id`.
2. A job queued during the request keeps them (`request_id` and
   `trace_parent` on the job), and the worker binds them again when it runs
   the job, so its log lines and spans name the same ids.
3. The model call's entry in the quality journal (Langfuse) carries both in
   its metadata.
4. The reply's `deliver_outbound` job is queued by that job, so the send
   keeps them too.

To follow one message: find its webhook in the logs (`request_id`), then
search the logs for that id, or open the trace by `trace_id`.

## Logs

`LOG_FORMAT=json` (production): one JSON object per line with `request_id`,
`trace_id`, `business_id`, `conversation_id`, `channel`, `job_name`,
`job_id`. Render keeps logs for a short time only, so production logs go
to an EU log store through a log drain (below).

### Render log drain to an EU log store (30 days)

1. Create a log source in an EU region of the log store (Better Stack
   Logs in Frankfurt, Grafana Cloud Logs in an EU stack, or Axiom EU) and
   copy its syslog endpoint and token.
2. In Render: Workspace settings -> Log Streams -> Add log stream, paste
   the endpoint (`host:port`) and the token. It applies to every service
   of the workspace (API, workers, cabinet, cron jobs).
3. In the log store set the retention of the source to 30 days and
   restrict access to the team.
4. Check: open the store's live tail and call `GET /readyz`; the access
   line appears within a minute with its `request_id`.

Logs carry ids and route names, never message texts or contact details.
They still name businesses and conversations by id, so the log store is a
sub-processor: add it to the sub-processor registry
(`app/registries/legal/`) and announce it to owners 30 days ahead
(`send_subprocessor_notices`) before the drain goes live.
