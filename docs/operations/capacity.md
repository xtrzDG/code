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
| `tests/storage/test_worker_pickup.py` | a customer message accepted by an API process is taken by a separate worker within 500 ms (its polls set to a minute, so only the wake-up can do it) | every CI run |
| `tests/storage/test_widget_burst.py` | 64 widget messages at once with a 20 s model (`SCRIPTED_LLM_LATENCY_MS=20000`): all accepted, `/readyz` stays 200 and `GET /v1/me` under 200 ms | every CI run |
| `tests/platform/test_connection_budget.py` | the Render Blueprints fit the database's connection limit during a deploy (below) | every CI run |

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
act as many client networks. Never deploy with these settings. The API
processes and the worker get production's pools and threads (render.yaml:
40 threads and 12 connections per API process; one worker with 20
threads, 16 connections, 12 model calls and the default lanes), four API
processes on the one runner; `tests/platform/test_load_stack_budget.py`
keeps them equal to the Blueprint and within Postgres's 100 connections.

```bash
C="docker compose -f docker-compose.yml -f perf/docker-compose.perf.yml"
$C up --detach --build --wait api   # the worker has no health check to wait for
$C up --detach worker
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

### Widget polls and the shared rate-limit counters (October 2026)

The weekly run of `bd4f29c` (`small` scale) met every cabinet budget
(p95 73–214 ms) but failed `widget_polling.js`: poll p95 1.12 s against
150 ms.

**The bottleneck.** Reproduced on a local stack (below), the database
said it at once. `pg_stat_statements` of the first reproduction: the
rate-limit upsert of a poll averaged 282 ms (45,126 calls) while every read of the poll stayed under
0.1 ms; `pg_stat_activity` sampled every 50 ms: on average 39 of the
API's 64 connections waited on `Lock:transactionid`, at most 62. Every
poll counts the same two rows of `rate_limit_buckets` (its business and
`widget-poll:platform`), and the adapter upserted them in a transaction,
read the counts back into Python, compared them with the limits there
and only then committed: the rows stayed locked for a round trip to a
busy Python process, so all polls of both API processes queued behind
each other, one Python round trip each.

**What changed.**

- `workshop.count_request_within_limits` (migration 1135) counts a
  request for every key, weighs each counter like `is_within_limit` and
  takes a refused request back out of every key, all in one autocommitted
  statement: the rows are locked only while it runs. Same contract (all
  or nothing, no bucket for a refused request, never two requests in the
  last place: `tests/storage/test_rate_limit_concurrency.py`, 32 threads
  over four pools; `test_rate_limit_parity.py`, request by request
  against the in-memory counters). Under the same load it averaged
  about 1 ms, and lock waits went from 39 connections to 0.05.
- A poll reads the web chat channel, the visitor's conversations and the
  visitor's ten newest messages (one keyset page on
  `messages_doc_conversation_idx`); when the cursor is among them and
  they reach back past it, the answer is the whole chat's
  (`widget_message_window`, `tests/storage/test_widget_poll_window.py`
  compares every cursor of random chats). The business document is no
  longer read (a channel exists only for an existing business), and a
  poll's cost no longer grows with the visitor's history; only a backlog
  of more than ten new messages, an unknown cursor or none reads the
  whole chat.

**Measured.** k6 1.3.0 ran `widget_polling.js` unchanged against a local
stack shaped like the load job's: Postgres 16 with its defaults (100
connections), the migrations, `seed-load --businesses 50 --messages
200000 --bookings 20000 --visitors 1000`, the API with two uvicorn
processes (64 threads and 32 connections each), the worker, the scripted
model at 800 ms. The machine had 4 vCPU shared with k6, Postgres and
other jobs (load average often 5–25), so absolute numbers are higher
than a dedicated runner's (the weekly run's 1.12 s was 4.8 s here);
before and after ran back to back from the same seeded database.

| Visitors (k6 VUs), run | Requests/s | Poll p50 | Poll p95 | Poll p99 | Message p95 | Counting statement (mean) | Connections waiting on a row lock (mean / max) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000, 5 min, before | 162 | 2,232 ms | 4,815 ms | 5,559 ms | 3,579 ms | 234 ms | 36 / 63 |
| 1,000, 5 min, after | 208 | 702 ms | 2,506 ms | 2,973 ms | 1,374 ms | 1.1 ms | 0.1 / 23 |
| 600, 3 min, before | 150 | 21 ms | 151 ms | 608 ms | 92 ms | 7.5 ms | 0.9 / 53 |
| 600, 3 min, after | 150 | 14 ms | 76 ms | 388 ms | 88 ms | 0.5 ms | 0 / 7 |
| 500, 2 min, before | 123 | 29 ms | 272 ms | 633 ms | 215 ms | 8.9 ms | 1.0 / 48 |
| 500, 2 min, after | 124 | 16 ms | 138 ms | 498 ms | 129 ms | 0.5 ms | 0 / 13 |
| 400, 3 min, before (two runs) | 100 | 19 / 17 ms | 84 / 106 ms | 298 / 448 ms | 82 / 104 ms | 3.8 ms | 0.4 / 55 |
| 400, 3 min, after (two runs) | 100 | 12 / 11 ms | 36 / 34 ms | 111 / 86 ms | 40 / 39 ms | 0.4 ms | 0 / 7 |

The database columns of the 400 rows are those of each pair's first run.
At 400 visitors the API processes also used a quarter less CPU after the
change (0.49–0.50 CPU against 0.61–0.69 for the same 100 requests a
second). On this machine the scenario now meets its thresholds up to
about 600 visitors (before: about 400); at 1,000 the poll p95 halved but
still misses 150 ms.

**What remains.** After the change Postgres is mostly idle during the
scenario (each poll's statements take about 0.1 ms; the counting
statement about 1 ms) and the limit is each API process: its 64 request
threads and its event loop share one interpreter lock, and with 250
polls a second on two processes the event loop waits for the lock more
than it works (each process used about 0.65 CPU while polls queued for
seconds). On this machine four processes (`WEB_CONCURRENCY=4`,
`DB_POOL_SIZE=12` to stay within 100 connections) measured a poll p95 of
453 ms where two measured 2.15 s; fewer threads (16) or a shorter
interpreter switch interval did not help. The weekly run on GitHub's
runner then still measured a poll p95 of 1.8 s with two processes, so the
load override now runs four of 12 connections each (production runs two
instances of one process each, half a CPU apiece: render.yaml sets no
`WEB_CONCURRENCY`). With four, the weekly run measured a poll p95 of
426 ms; the next section takes the Python out of a poll.

### Widget polls: less Python per poll (October 2026)

The weekly run of `5d94452` on four API processes measured a poll p95 of
426 ms (p50 87 ms) against 150 ms while Postgres idled: the cost was
Python per poll, and every millisecond of it queues the other polls of
the process behind one interpreter lock.

**Where a poll's CPU went.** Polls ran one after another through the
whole application in one process (the middlewares, FastAPI, the request
thread, Postgres with row-level security, the load dataset), measured
with py-spy (samples of the lock holder) and CPU probes per thread
(`time.thread_time()` around each step, so its system calls count too).
CPU per poll, mean of two back-to-back rounds:

| Step | Before | After |
| --- | ---: | ---: |
| Event-loop thread: middlewares, route matching, FastAPI, the hop to a request thread | 1,045 µs | 668 µs |
| Rate-limit count (one statement) | 444 µs | 440 µs |
| The web chat channel (every channel of the business decoded) | 659 µs | 18 µs (remembered) |
| The visitor's conversations | 575 µs | 426 µs |
| The newest messages | 760 µs (ten decoded) | 434 µs (ten positions) |
| Read session: begin with the scope, commit | in the rows above | 258 µs |
| Whole process | 3,826 µs | 2,570 µs (−33 %) |

- **Statements.** A poll ran 13: the count, then begin, the scope
  settings, the read and commit for each of three reads. On this machine
  a statement costs about 150 µs of CPU in the request thread: psycopg,
  and the system calls of a thread that sleeps until Postgres answers
  and is woken (a sleep and a wake-up alone cost 50–70 µs of CPU here).
- **Decoding.** About 54 µs a message, 29 a conversation, 21 a channel
  (typed primitives validate field by field in Python): a poll decoded
  up to four channels, its conversations and ten messages to learn that
  nothing was new.
- **Route matching**, 0.45 ms: the widget router came after about 250
  other routes, and each is compared in turn.
- **A second hop to a request thread**: FastAPI validates the DTO a sync
  route returns again, in a request thread, before serializing it.
- Smaller: the access line 23 µs (text) to 29 µs (JSON), the garbage
  collector 25 µs. With Sentry on (production) a poll cost about 590 µs
  more: 260 µs its wrapping of every request, the rest the 5 % of polls
  it traced (milliseconds each).

**What changed.**

- The channel router (webhooks and the widget) is matched first; no
  other route shares its paths (`test_route_matching_order.py`).
- The poll serializes its answer itself: the same bytes and headers as
  FastAPI's, one hop to a request thread instead of two
  (`serialized_json_response`, `test_widget_poll_answer.py`).
- Read sessions (`StorageReadSessionContract`): the poll's reads share
  one connection and one transaction begun together with its row-level
  security settings in one round trip, so each read is one statement.
  Writes and reads in another scope inside a session keep their own
  connections, so nothing else runs on its transaction; each statement
  still sees what was committed when it ran (read committed), as before.
  The count stays outside, alone, so its row locks last only while it
  runs.
- The newest ten messages are read as positions (id and time from the
  index columns, `page_positions_by`); only the messages after the
  cursor are read in full, none when nothing is new.
- An open web chat is remembered for 10 s per process
  (`OpenChatMemory`): polls skip the channel read. Only open chats are
  remembered, so a widget switched on answers at once; **a widget
  switched off answers polls for up to 10 s more** (its messages are
  refused at once).
- Sentry traces widget polls at a hundredth of
  SENTRY_TRACES_SAMPLE_RATE (`sentry_trace_sampling`): 3,075 → 2,899 µs
  per poll in-process with Sentry on; errors are reported as before.

A poll now runs five statements (the count, begin with the scope, the
conversations, the positions, commit) and decodes one conversation. The
answers are unchanged: every cursor of random chats gets the whole
chat's answer, in memory and on Postgres with the read session
(`tests/storage/test_widget_poll_window.py`).

**Measured.** k6 ran `widget_polling.js` unchanged with 1,000 visitors on
four API processes (production's 40 threads and 12 connections each) and
one worker as production's, against the harness of the section above;
before and after ran back to back from the same seeded database. Other
jobs kept the machine's load at 9–25 on its 4 vCPU, so latencies vary
from pair to pair; CPU per request varies less.

| Run (k6, 1,000 visitors) | Poll p50 | Poll p95 | Message p95 | API CPU per request | Postgres CPU per request |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5 min, before / after (pair 1, load 13–19) | 46 / 19 ms | 479 / 213 ms | 311 / 204 ms | 4,822 / 3,784 µs | 3,259 / 2,795 µs |
| 5 min, before / after (pair 2, load 14–24) | 165 / 41 ms | 2,618 / 404 ms | 1,131 / 430 ms | 5,781 / 3,647 µs | 3,649 / 2,721 µs |
| 2 min, polls only, before / after | 18.9 / 9.3 ms | 362 / 51 ms | — | 4,424 / 3,088 µs | 2,056 / 1,396 µs |
| 2 min, quieter machine (64 threads, the worker's defaults), before / after | 44 / 12 ms | 487 / 63 ms | 295 / 77 ms | 4,295 / 3,287 µs | 3,253 / 2,734 µs |

CPU per request fell by 21–37 % in the server (30 % with polls only, a
third in-process), not by half: uvicorn, the sockets and the access line
add about 0.5 ms per request that did not change, and the five remaining
statements and the hop to a request thread cost about 0.15 ms each. The
fewer round trips matter most under contention: the old poll's CPU grew
with the machine's load (4,295 to 5,781 µs), the new one's much less
(3,287 to 3,784 µs). The poll p95 met the 150 ms threshold on the
quieter machine (63 ms; 51 ms with polls only) but not while the other
jobs loaded it (213 and 404 ms); with two API processes (production's
count) it was 270 ms at a load of 25. The weekly run on a dedicated
runner decides it. `tests/perf` at the small scale measured the poll at
p50 4.4 ms, p95 5.7 ms (budget 60 ms; 9.1 and 15.7 ms in a run of the
previous commit on a busier machine).

**What remains.** The next levers, in order of what they would save:

- A read model of each visitor's chat head (the latest message id and
  time, handed off or not), kept with every web chat message write: a
  poll that finds nothing new would be the count and one indexed read,
  no session and no documents.
- Database access without a request thread for the poll (an async
  psycopg pool), so a poll needs no hop and no thread wake-up.
- Sentry's wrapping of every request (about 260 µs with Sentry on).

## What one process carries

- **Request threads.** An API instance answers `THREADPOOL_SIZE` (64 by
  default, 40 in render.yaml) requests at once. Reads of the cabinet and
  widget polls take milliseconds (the table above), so polling is cheap:
  1,000 visitors polling every 4 seconds are 250 requests a second, a few
  threads busy in the database; the Python side of the processes is the
  limit there: a poll costs an API process about 3 ms of CPU on the load
  harness, so 250 a second take three quarters of a CPU (production's
  two instances have half a CPU each; "Widget polls: less Python per
  poll" above).
  A widget message is stored and queued in one transaction and answered
  `202` at once; the worker answers it like every channel's message and
  the widget shows the typing dots until a poll brings the answer. A slow
  model therefore holds worker threads, never request threads: scale
  workers for chat traffic, API instances for requests. Only the owners'
  test chat still answers in the request, on at most
  `TEST_CHAT_MAX_CONCURRENCY` (4) threads per instance; one more owner gets
  `429` "try again in a few seconds". Polls that arrive in lockstep queue
  behind each other (one process runs Python one request at a time):
  60 visitors polling at the same instant saw a p95 of 0.5 s, spread
  over the 4 seconds 25 ms; real visitors open their pages at random
  moments, and the k6 scenario spreads them the same way.
- **Webhooks.** A channel webhook only verifies, stores the update and
  queues it; the answer comes from the worker. One API process
  acknowledges about 120 webhooks a second on 4 shared vCPU (10 ms each
  at 50 a second); at 200 a second it falls behind and the wait grows to
  seconds. Two processes (`WEB_CONCURRENCY=2`; the load override now
  sets four) took 200 a second for 20 s with nothing dropped and a p95 of
  0.6 s.
  Plan one API process per 100 webhooks a second of peak.
- **Worker throughput.** A worker answers `inbound` messages
  `WORKER_LANE_CONCURRENCY` at a time (8 by default). At 800 ms per model
  call a turn took about 1.1 s on the load harness (the rest is storage
  round trips and Python), so one worker answers 7–8 messages a second:
  a one-minute burst of 200 messages a second (12,000 messages) takes
  one worker about 25 minutes to drain, ten workers about 3. 1,000
  widget visitors writing every two minutes send 8.3 a second, more
  than one worker answers: in the k6 scenario with production's one
  worker the pickup delay grew all along (p50 16 s, p95 20 s after five
  minutes; the weekly run's 12 s and later 70 s), with two workers it
  stayed at p50 87 ms, p95 1.4 s. Production runs one worker
  (render.yaml), and a second instance does not fit its connection
  budget at 16 connections (2 x 2 x 17 more); raise its `inbound`
  concurrency within `LLM_MAX_CONCURRENCY` and `DB_POOL_SIZE` (a turn
  holds a connection while it runs) or shrink the pools first. Raise the `inbound` concurrency
  (keep `DB_POOL_SIZE` and the provider's rate limits in mind) or add
  workers when the queue's wait grows (the admin system page,
  `/admin/system`: the `inbound` lane's oldest wait; the
  `inbound_backlog` alert pages above 120 s, `docs/operations/slo.md`).
- **Database connections.** Every process keeps up to `DB_POOL_SIZE`
  connections (half of `THREADPOOL_SIZE` unless set) and closes those idle
  for `DB_POOL_MAX_IDLE_SECONDS` (300) down to `DB_POOL_MIN_SIZE` (2), so a
  burst's peak does not stay open. `THREADPOOL_SIZE` stays above
  `DB_POOL_SIZE`: a request holds a connection for milliseconds, and one
  waiting a moment for it is better than one refused. See "Connection
  budget" for the sum.
- **Turn places before locks.** A customer turn first takes one of the
  process's `LLM_MAX_CONCURRENCY` turn places and only then the
  customer's lock, a session advisory lock that pins a connection for the
  whole turn. A turn waiting for a place (a slow model, a burst) holds no
  connection, so waiting turns cannot drain the pool.

## Pickup: from a customer message to a worker

The pickup delay is the time from the moment a job became due to the
moment a worker claimed it. Every claim logs it:

```
Picked up job process_inbound_message on the inbound lane 41 ms after it was due
```

with the structured fields `pickup_delay_ms`, `lane`, `attempt`,
`job_name` and `job_id` (one JSON line in production; search Render's
logs for `pickup_delay_ms`). The SLI is the p95 of `pickup_delay_ms` of
`process_inbound_message` on the `inbound` lane; the target is 500 ms.

- **How it stays low.** The queue inserts a job and runs
  `pg_notify('workshop_jobs', <lane>)` in the same transaction: Postgres
  delivers the notification only when the job commits (a rolled-back
  enqueue wakes nobody). Each worker keeps one `LISTEN workshop_jobs`
  connection (`application_name` `assistant-workshop-job-wakeup`, on
  `LIVE_EVENTS_DATABASE_URL` or `DATABASE_URL`; it reconnects with
  backoff like the API's live events listener) and wakes the lane's idle
  threads at once.
- **The safety net.** Lane threads still poll: the `inbound` lane every
  `WORKER_INBOUND_POLL_SECONDS` (2), the others every
  `WORKER_POLL_SECONDS` (15). The first polls are staggered (thread i of
  n waits i/n of the period), so the threads of a lane never query
  together. After a reconnect every lane polls at once.
- **Reading it.** Pickups spread evenly up to 2,000 ms: wake-ups are not
  arriving (the LISTEN connection is down, or `DATABASE_URL` goes through
  a transaction pooler without `LIVE_EVENTS_DATABASE_URL`), and only
  polling finds the jobs. Growing far beyond that: every `inbound` thread
  is busy; raise the lane's concurrency or add workers (above). A lane
  thread claims its next job as soon as one ends, so a busy lane has no
  idle gap to win back in the claim itself.
- **Lost leases.** "Job … lost its lease" means another worker could
  take the job over (it ran past its lease without heartbeats). Before
  October 2026 a job that finished while the heartbeat ran was reported
  so too, about a second after its pickup (one such line in the weekly
  run); the runner now lets go of a job before settling it and the
  heartbeat reports only jobs it still holds.

## Readiness under load

`GET /readyz` (Render's health check, which takes an instance out of
traffic) fails only when the instance cannot serve at all: the database
does not answer (`select 1`, 2 s) or a migration of this build is missing.
A pool with no free connection (the probe's `pool_exhausted`) is load,
not a fault: the report stays `ready` (`200`) with the database and pool
checks `degraded` and the pool's `exhausted_seconds`, and the migrations'
last reading is reused instead of waiting for a connection. Only a pool
exhausted for more than 30 s in a row fails it (`503`, and an error in the
log): then requests are stuck, not busy. `GET /healthz` (liveness) never
touches the database.

## Connection budget

Render's `basic-256mb` Postgres accepts 100 connections. The worst moment
is a deploy: Render starts the new instances of the API and the worker
before it stops the old ones, while the backup may run and the migration
runs before. `tests/platform/test_connection_budget.py` reads every
Blueprint and checks

```
2 x API instances x (DB_POOL_SIZE + 1 LISTEN)
+ 2 x workers x (DB_POOL_SIZE + 1 LISTEN)
+ backup 2 + migrate 1 + reserved 5   <=   the plan's limit
```

(reserved: Postgres's three superuser connections, an operator's psql and
Render's own checks). Production (`render.yaml`): 2 x 2 x (12 + 1) = 52
for the API, 2 x (16 + 1) = 34 for the worker, 2 + 1 + 5: 94 of 100.
Staging (one API instance) sets the same pools. The defaults (64 threads,
32 connections) would not fit: a Blueprint without `DB_POOL_SIZE` fails
the test.

When more is needed (a third API instance, a second worker, larger
pools), pick one route and update the Blueprint and the test together:

- **A larger database plan.** Add its connection limit (Render, "Postgres
  connection limits") to `PLAN_CONNECTION_LIMITS` in
  `tests/platform/connection_budget.py`.
- **PgBouncer in front.** Run PgBouncer as a private service in session
  mode with `max_db_connections` below the plan's limit minus the
  reserve, and point `DATABASE_URL` of the API and the worker at it: a
  deploy's peak then waits in PgBouncer instead of failing with "too many
  clients", and idle pools (closed after 300 s) free their server
  connections. Transaction mode is not enough: a customer turn holds a
  session advisory lock on its connection
  (`app/adapters/locks/postgres_advisory_lock_adapter.py`), and LISTEN
  needs a session (`LIVE_EVENTS_DATABASE_URL` then names the direct
  address). Count PgBouncer's limit, not the pools, in the test.
- **Smaller pools.** Lower `DB_POOL_SIZE` per process; requests queue
  for a connection a little longer, and readiness stays green while they
  do.

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
- `migrations/1042_list_pages_and_aggregates.sql` and
  `1122_online_lookup_columns.sql` add the sort and group columns with
  indexes that start with `business_id`;
  `tests/storage/test_list_query_plans.py` keeps every list on its index.
- Periodic jobs ask by indexed predicates or walk the businesses in keyset
  batches of 200 (`walk_businesses`); no repository reads a whole table.

## Known limits

- The admin client list reads stored standings (one keyset page, database
  counts); the `refresh_client_standings` job behind it summarizes every
  business each 15 minutes (a few indexed counts each, in batches of 200)
  and ranks them with only their sort keys in memory: fine for thousands
  of businesses, a run of minutes at tens of thousands. A search by part
  of a name walks at most 2,000 standings per request.
- The admin metrics page still reads every business (walked in batches
  of 200, but all held for the funnel): fine for thousands.
- The customer list and the knowledge list page in the database
  (migration 1122); the customer search finds exact names, phones and ids
  through indexes and walks at most 500 customers for a part of a name.
- A widget poll reads where the visitor's ten newest messages stand and
  only the messages after its cursor; only a backlog longer than that,
  an unknown cursor or none reads the visitor's whole chat (bounded by
  one visitor's chat, not by the business).
- A widget switched off still answers polls for up to 10 s in every API
  process (`OpenChatMemory`); its messages are refused at once.
- Every widget poll of the platform counts the same rate-limit row
  (`widget-poll:platform`): one short statement each (migration 1135),
  so it serializes polls only for about a millisecond apiece.
- Seeding the full dataset took 21 minutes locally (the demo part of each
  business dominates); the weekly budgets job allows two hours.
- The scripted model answers every message with one sentence; a
  conversation the engine hands to staff afterwards gets no model call,
  so widget messages of such visitors measure storage, not the model.
