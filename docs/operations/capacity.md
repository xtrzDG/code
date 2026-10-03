# Capacity and performance budgets

What the platform is measured against, how to run the measurements, what
one API instance and one worker carry, and where the known limits are.
`docs/operations/deploys.md` covers releases; this page covers load.

## What is measured, and where

| Check | What it guards | Runs |
| --- | --- | --- |
| `tests/perf` (`uv run pytest -m perf tests/perf`) | p95 latency of the requests people wait for, over a seeded Postgres, against fixed budgets | weekly and on demand (`.github/workflows/perf.yml`); excluded from the normal `pytest` run |
| `perf/baseline.json` + `scripts/perf_compare.py` | the same p95s against the last accepted run: more than 20% (and more than 1 ms) slower fails | weekly, after `tests/perf` |
| `perf/k6/*.js` | concurrency against docker compose: cabinet browsing, 1000 polling widget visitors, webhook bursts of 200 messages a second | weekly and on demand |
| `tests/storage/test_list_query_plans.py` | every cabinet list, count and sum uses its index on realistic tables (EXPLAIN) | every CI run |
| `tests/architecture_policy/test_lists_page_in_the_database.py` | lists, cards and dashboards never load a business's whole history | every CI run |

### Latency budgets (tests/perf)

Each request kind runs 20 untimed and 200 timed times through the whole
application (FastAPI, operators, repositories, Postgres with row-level
security; no network), spread over the seeded businesses. The budget is
the p95 in milliseconds:

| Request | Route | p95 budget |
| --- | --- | ---: |
| authenticate | `GET /v1/me` (bearer token to user) | 25 ms |
| conversations list | `GET /v1/businesses/{id}/conversations` (first page of 50) | 150 ms |
| conversation detail | `GET /v1/businesses/{id}/conversations/{id}` | 150 ms |
| availability | `GET /v1/businesses/{id}/availability?date=…&party_size=2` | 120 ms |
| dashboard | `GET /v1/businesses/{id}/dashboard` (last 30 days) | 300 ms |
| widget poll | `GET /v1/widget/{id}/messages?after=…` | 60 ms |

`PERF_SCALE` picks the dataset: `full` (the weekly run: 500 businesses,
2,000,000 messages, 200,000 bookings, 1,000 widget visitors), `medium` (a
tenth) or `small` (default: 10 businesses, 20,000 messages). `PERF_REPORT`
names the JSON file the results go to.

Measured at the full scale (a local run on 4 vCPU and 16 GB shared with
other jobs, Postgres 16 on the same machine; seeding took
21 minutes). These are also the first `perf/baseline.json`; refresh
it from the first weekly run on GitHub's runners (below), which differ.

| Request | p50 | p95 |
| --- | ---: | ---: |
| authenticate | 7 ms | 14 ms |
| conversations list | 48 ms | 69 ms |
| conversation detail | 27 ms | 38 ms |
| availability | 24 ms | 39 ms |
| dashboard | 55 ms | 78 ms |
| widget poll | 10 ms | 19 ms |

### The baseline

`perf/baseline.json` holds the p95s of an accepted full-scale run. The
weekly job compares its own run with it and fails when a request got more
than 20% slower (differences under 1 ms are timer noise and pass). To
accept new numbers (a faster query, a new runner type, or a slowdown with
a reason), run the workflow by hand with `update_baseline` checked,
download the `perf-report` artifact and commit its `baseline.json` in a
pull request that says why. Never raise the baseline to silence a
regression nobody explained.

## The load dataset: `workshop seed-load`

```bash
uv run python -m app.gateways.cli.seed_load --manifest perf/manifest.json
uv run python -m app.gateways.cli.seed_load --businesses 20 --messages 40000 \
    --bookings 4000 --visitors 100 --manifest perf/manifest.json
docker compose run --rm -T api seed-load --manifest - > perf/manifest.json
```

It needs `DATABASE_URL` and is refused with `APP_ENV=production`. Every
load business is a demo business (the Tbilisi restaurant and the Berlin
salon in turn, numbered): its own verified owner and staff member, the
foundation, assistant versions assembled from it, a month of demo
activity, and then a bulk history written through the repositories in
batches of 1,000 documents per transaction: one contact per chat
conversation, ten-message conversations over the last four months (model
usage and cost on the assistant's messages), bookings from ten months
ago to two months ahead (upcoming ones with their reminder already sent)
and website-widget visitors chatting right now. The same `--seed` builds
the same shape.

The manifest lists, per business, its id, the owner's bearer token (a
real session for 30 days), 20 recent conversations, the widget visitors
(session key and latest message) and, for the restaurants, the Telegram
channel and the webhook secret token Telegram would send. It is a secret
of the load database: `perf/manifest.json` is ignored by git; delete it
with the database.

## Load scenarios: k6 against docker compose

`perf/docker-compose.perf.yml` turns the local compose stack into a load
target: `LLM_PROVIDER=scripted` with `SCRIPTED_LLM_LATENCY_MS` (default
800, a real provider's typical answer, so request threads and the worker
stay busy as long as in production), provider hosts resolved to nowhere
(replies to the made-up Telegram bots fail at once and the outbox retries
them; nothing leaves the machine), and `FORWARDED_ALLOW_IPS="*"` so k6 can
act as many client networks. Never deploy with these settings.

```bash
C="docker compose -f docker-compose.yml -f perf/docker-compose.perf.yml"
$C up --detach --build --wait api worker
$C run --rm -T api seed-load --businesses 50 --messages 200000 \
    --bookings 20000 --visitors 1000 --manifest - > perf/manifest.json
$C --profile load run --rm k6 run /perf/k6/cabinet_browsing.js
$C --profile load run --rm k6 run /perf/k6/widget_polling.js
$C --profile load run --rm k6 run /perf/k6/webhook_burst.js
$C down --volumes
```

| Scenario | Load | Thresholds (the run fails above them) |
| --- | --- | --- |
| `cabinet_browsing.js` | 100 owners (`CABINET_USERS`) for 5 minutes: dashboard, feed, a card, bookings, availability, with think time | errors < 1%; p95 per page: dashboard 800 ms, others 500 ms |
| `widget_polling.js` | 1,000 visitors (`WIDGET_VISITORS`) polling every 4 s, each writing about every 2 minutes | errors < 1%; poll p95 150 ms; message p95 the model latency + 1.5 s |
| `webhook_burst.js` | 200 Telegram updates a second (`WEBHOOK_RATE`) for a minute over the restaurants' bots | errors < 1%; p95 1 s, p99 3 s; fewer than 100 dropped iterations |

Outside CI, `k6 run -e MANIFEST=$PWD/perf/manifest.json -e
API_URL=http://localhost:8000 perf/k6/cabinet_browsing.js` runs a scenario
against any stack you seeded (only ever a load-test one).

## What one process carries

- **Request threads.** An API instance answers `THREADPOOL_SIZE` (64)
  requests at once. Reads of the cabinet and widget polls take
  milliseconds (the table above), so polling is cheap: 1,000 visitors
  polling every 4 seconds are 250 requests a second, a few threads busy.
  A widget message holds its thread for the whole model answer: with
  800 ms of model latency one instance answers at most about 80 widget
  messages a second, less what else it serves. Scale API instances for
  chat traffic, not for lists. Polls that arrive in lockstep queue
  behind each other (one process runs Python one request at a time):
  60 visitors polling at the same instant saw a p95 of 0.5 s, spread
  over the 4 seconds 25 ms; real visitors open their pages at random
  moments, and the k6 scenario spreads them the same way.
- **Webhooks.** A channel webhook only verifies, stores the update and
  queues it; the answer comes from the worker. One API process
  acknowledges about 120 webhooks a second on 4 shared vCPU (10 ms each
  at 50 a second); at 200 a second it falls behind and the wait grows to
  seconds. Two processes (`WEB_CONCURRENCY=2`, as the load override sets)
  took 200 a second for 20 s with nothing dropped and a p95 of 0.6 s.
  Plan one API process per 100 webhooks a second of peak.
- **Worker throughput.** A worker answers `inbound` messages
  `WORKER_LANE_CONCURRENCY` at a time (8 by default). At 800 ms per model
  call that is about 10 answers a second per worker: a one-minute burst
  of 200 messages a second (12,000 messages) takes one worker about 20
  minutes to drain, ten workers about 2. Raise the `inbound` concurrency
  (keep `DB_POOL_SIZE` and the provider's rate limits in mind) or add
  workers when the queue's wait grows (admin jobs page; the
  `inbound` lane's oldest queued job).
- **Database connections.** Every process keeps up to `DB_POOL_SIZE`
  connections; the sum over API instances and workers must stay below the
  Postgres limit.

## How lists stay fast as history grows

- Lists of growing collections (conversations, messages, bookings, leads,
  handoffs, unanswered questions, the audit log) read one keyset page in
  the database (`page_by`): the cost of a page does not depend on how
  many pages came before it or how much history the business has.
- Counts, sums and the dashboard group in the database (`count_by`): the
  dashboard reads no conversation, message, booking or handoff.
- A page's related documents come in one statement: contacts by id
  (`get_many`), message counts (`count_by`) and each conversation's
  newest message (`latest_by`, one index probe per conversation).
- `migrations/1042_list_pages_and_aggregates.sql` adds the sort and group
  columns with indexes that start with `business_id`;
  `tests/storage/test_list_query_plans.py` keeps every list on its index.

## Known limits

- The admin client list summarizes each business with a few indexed
  counts: fine for hundreds of businesses, to be replaced by stored
  per-business figures before thousands.
- The contacts list and the knowledge list still page in memory (a
  business's contacts are read for a page); contacts grow with customers
  and need a stored last-activity time to page in the database.
- A widget poll reads the messages of the visitor's own conversations:
  bounded by one visitor's chat, not by the business.
- Seeding the full dataset took 21 minutes locally (the demo part of each
  business dominates); the weekly budgets job allows two hours.
- The scripted model answers every message with one sentence; a
  conversation the engine hands to staff afterwards gets no model call,
  so widget messages of such visitors measure storage, not the model.
