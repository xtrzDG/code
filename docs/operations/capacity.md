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

`tests/perf/test_reply_budget.py` times a customer's reply end to end on
the game days' two-process world (an API and a worker process, WhatsApp
through Meta's signed webhook, fake Meta and OpenAI on 127.0.0.1, a model
that answers after 2 s, lane polls a minute apart so only wake-ups count):
a finished question is taken at the API's commit (`queue_to_claim_ms`
under 1 s) and answered within 3 s of the claim and 6 s of the webhook;
a fragment is taken by the due-time timer after `MESSAGE_COALESCE_SECONDS`
and stays within the same budget. The first question is the fresh
worker's first turn: the worker loads the reply guard's CLDR data before
its lanes start (otherwise the first customer after a deploy waited
1.4 s longer). It asserts its budgets itself and writes nothing to the
report.

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
the same shape. Four businesses are stored at a time (`STORING_THREADS`
of `SeedLoadOrchestrator`): building and encoding documents is Python
work, writing them the database's, and on four threads the two overlap
instead of taking turns; the manifest keeps the plan's order. A month of
demo activity writes each kind of document in one batch.

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
perf/wait-for-drain.sh "before cabinet browsing"
$C --profile load run --rm k6 run /perf/k6/cabinet_browsing.js
perf/wait-for-drain.sh "before widget polling"
$C --profile load run --rm k6 run /perf/k6/widget_polling.js
perf/wait-for-drain.sh "before the webhook burst"
$C --profile load run --rm k6 run /perf/k6/webhook_burst.js
$C down --volumes
```

Before each scenario `perf/wait-for-drain.sh` polls the database until the
worker has drained the customer lanes (no `inbound` or `outbound` job due
or running; a send queued for a later attempt does not count), at most 10
minutes, then goes on with a warning: the widget visitors' messages are
answered by one worker for minutes after their scenario, and that backlog
would otherwise load the webhook burst. Both jobs of `perf.yml` write the
runner's CPUs, CPU model and memory and the seed time into the job
summary (`scripts/perf_runner.py`), and every wait its outcome, so a slow
runner shows next to its numbers. The load job has no project environment:
it runs the script with uv's Python 3.14 (`uv run --no-project`), never the
runner image's older python3, and the step only informs (a failed summary
never keeps the waits and scenarios from running);
`tests/platform/test_workflow_python.py` holds every workflow to uv's Python
for repository code.

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
  (Since 2026-10-12 a session pins its connection, and writes inside it
  run after the session committed its reads, on the same connection: see
  "The weekly run of 2026-10-12".) Each statement still sees what was
  committed when it ran (read committed), as before. The count stays
  outside, alone, so its row locks last only while it runs.
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

### The weekly run of 2026-10-12: a slow runner and a longer seed

The weekly run of `d3b71d6` failed `widget_polling.js` (poll p95 195 ms
against 150 ms), yet every request of the run was 5 to 10 times slower
than the week before (cabinet pages p95 236–381 ms against 43–74 ms on
2026-10-07), and so were steps the code never touches there: seeding the
same dataset took 170 s against 97 s. The same latency budgets run on one
machine for both commits (`fa1132e`, the last green load run, and
`d3b71d6`) gave the same p95s, the poll 14–22 ms on both: the runner was
slow, not the code.

The full-scale budgets job of that run hit its 120-minute timeout (it took
106 minutes on 2026-10-05). On one machine at the medium scale, seeding
took 160 s at `a410fb0` (2026-10-05) and 180 s at `d3b71d6`, and owner
requests grew by about 5 ms at p50: every one now passes the generic API
limit (`count_request_within_limits`, the spend guard), `/v1/me` reads the
partner flag, availability reads the calendar links, busy times and the
waitlist, the conversation list one more audit row. The job now allows
180 minutes; the budgets and the baseline are unchanged.

**Headroom (H6, the same day).** The code then got the headroom back
without touching a gate: the k6 thresholds, the rates, visitor counts and
durations, `BUDGETS_MS` and `perf/baseline.json` are as they were, and
every request the generic API limit counted it still counts.

- *A transaction opens with its scope.* `begin; select set_config(...)`
  goes as one message, and so does a unit of work's savepoint with its
  scope (`scoped_transactions.py`): no statement of the block runs before
  its row-level security scope, one round trip earlier than before.
- *Read sessions pin their connection and lend it.* A session's reads
  share one transaction begun at the first read with that read's scope;
  a read in another scope sets its scope first. Other work in the block
  (a write, a unit of work, a lock, the rate-limit count) gets the same
  connection after the session committed its reads, so a write commits
  on its own at once, as before, and a session never waits for a second
  connection (`test_read_session_lending_on_postgres.py` proves it on a
  pool of one). Authentication, `/v1/me` (with the partner flag), the
  conversation list and card, availability and the dashboard each read
  in one session.
- *Reads whose answer was unused.* Availability reads no busy times for a
  business that links no calendar (only a link brings them; the stale
  refresh already read the links). A Telegram webhook reads its channel
  once: the activity stamp comes from that read, and only a button tap
  reads the channel again to answer it. A webhook's dedupe, inbox row, job
  and wake-up stay one transaction, acknowledged after it commits.
- *Seeding* stores four businesses at a time and writes a month of demo
  activity in one batch per kind (above).
- *The weekly run says what it ran on.* Each k6 scenario starts once the
  worker drained the customer lanes of the scenario before (bounded), and
  the job summary names the runner's CPUs and the seed time (above).

Round trips per request, counted from libpq's protocol trace (the same on
any machine; `tests/storage/test_request_statement_counts.py` fails a
request over its count):

| Request | Before | After |
| --- | ---: | ---: |
| `GET /v1/me` (authentication, the limit, the user) | 25 | 11 |
| Conversation list | 42 | 22 |
| Conversation card | 78 | 31 |
| Availability | 49 | 21 |
| Dashboard | 81 | 28 |
| Widget poll | 9 | 8 |
| Telegram webhook (transactions) | 27 (4) | 14 (2) |

Timings, before and after alternating on one machine (other jobs kept
its load at 9–16 on 4 vCPU, so single runs vary by a fifth; medians of
the pairs):

| Measured | Before | After |
| --- | ---: | ---: |
| In-process (3 businesses, 300 requests, 3 pairs), CPU per request: `/v1/me` | 12.4 ms | 10.0 ms |
| the same, availability | 23.1 ms | 20.8 ms |
| the same, conversation list | 46.4 ms | 44.1 ms |
| the same, Telegram webhook | 12.1 ms | 9.9 ms |
| In-process p50 / p95: `/v1/me` | 21.6 / 59.2 ms | 14.3 / 41.2 ms |
| the same, availability | 54.9 / 112.8 ms | 41.8 / 92.5 ms |
| the same, Telegram webhook | 27.9 / 79.0 ms | 16.2 / 50.8 ms |
| `workshop seed-load` operator, small scale (3 pairs) | 41.9 s | 22.6 s |
| `tests/perf` small: seed_seconds (3 pairs) | 30.7 s | 19.3 s |

`tests/perf` at the small scale (3 pairs; p50 / p95 in ms): before, one
run of three failed two budgets on the busy machine (authenticate p95
39.6 ms over its 25, the conversation list 160.5 over 150); after, every
run met every budget. Medians: authenticate 12.2 / 21.8 → 10.1 / 20.2,
conversation list 74.3 / 132.3 → 64.8 / 104.5, conversation card 34.7 /
80.5 → 28.7 / 56.6, availability 30.8 / 72.5 → 33.2 / 76.2, dashboard
74.1 / 125.1 → 64.8 / 118.1, widget poll 9.2 / 18.0 → 11.3 / 18.1. The
kinds whose round trips fell most got faster; availability and the poll
moved within the machine's noise (in-process, availability's CPU fell by
a tenth). At the medium scale (4 pairs) the machine's load rose
from 6 to 23 while they ran, more than any change measured here: seeding
took 207–406 s before and 119–231 s after (median 295 → 166 s); the
requests' p50 medians moved by under 15 % either way (authenticate 16.8 →
14.5 ms, availability 55.7 → 51.5 ms, the others within 1 ms), and within
each pair the new build was faster for every kind in the two busiest
pairs (availability 77 → 56 and 107 → 50 ms, the dashboard 134 → 100 and
147 → 100 ms), mixed in the quietest and slower for every kind in one
pair, the widget poll's included, which this change barely touched.
Wall-clock time on a shared machine cannot settle a few milliseconds; the
round-trip counts above and the CPU per request are the measure.

What the counts leave: the conversation list spends its time decoding
150 documents a page (typed fields validate one by one), not on the
database; a webhook's unit of work still opens a savepoint per write and
one for the job queue's own unit (11 of its 14 round trips); the
waitlist's held places are read for every availability, as only a read
shows whether there are any.

**Wave 19 on top (2026-10-13).** Two packages of the wave need one more
round trip each on three of the counted requests; the test's counts
moved by exactly that, every other count stayed:

- `GET /v1/me` 11 → 12: the cabinet lists the locations a person reaches
  through a brand (R17-BRANDS), so the user's brands are read by member
  (one indexed lookup, inside the request's read session). Nothing the
  request already holds says whether a person is in any brand.
- Conversation list 22 → 23 and card 31 → 32: an audit entry never
  changes once chained (R13-AUDIT-TRAIL, migration 1193), so a repeated
  view is counted in `audit_view_counts` instead of rewriting the entry.
  The first repetition of a view finds no count yet (the row-locked
  modify misses, its own transaction) and then inserts one (a second
  transaction): two write transactions where H6 had a read in the
  session and one write. Every later repetition is one row-locked update
  (four round trips, one fewer than H6's read plus rewrite). Both writes
  now run in the business's own row-level security scope, not
  platform-wide. The counted request is the second of two, so it pays
  the first repetition.

The availability (21), dashboard (28), widget poll (8) and Telegram
webhook (14 in 2 transactions) counts are unchanged with all six
packages merged.

**Wave 20: two database roles (2026-10-22).** A request now runs on two
pools (`docs/operations/deploys.md`, "Database roles"), and a business's
read session can no longer turn platform-wide in the middle of its
transaction: the tenant role sees one business whatever the session sets.
Its platform reads (the business, the audit entries) left the session
and became transactions of their own, two round trips more each
(`begin` with the scope, the read, `commit`). The platform role sees
every row whatever `app.business_id` says, so a platform-wide read
outside a transaction now runs as one statement in autocommit
(`scoped_read`), and the counts fell instead: `/v1/me` 12, the
conversation list 21, the card 30, availability 18, the dashboard 25,
the widget poll 8 and the Telegram webhook 12 in 2 transactions,
counted over both pools together (`tests/storage/statement_trace.py`,
`traced_together`). The budgets stay where they were.

### The runs of 2026-10-19 and 2026-10-20: a saturated runner, and a poll of two round trips

The scheduled run of `28a3a3c` (backend as `b746ddd`) failed
`widget_polling.js` on 2026-10-19 and again on its re-run of 2026-10-20
on one threshold only: the poll p95 was 213 ms and 254 ms against
150 ms (median 35–37 ms, p90 about 145 ms, max 3–3.7 s). Everything else
held: no failed request, about 250 requests a second, 73,000
iterations, the message p95 277–368 ms against 2,300 ms. Both jobs carry
GitHub's notice that `ubuntu-latest` moves to Ubuntu 26 from 2026-10-19.

**No code regression.** On one harness (Postgres 16, each commit's
migrations and `seed-load --businesses 50 --messages 200000 --bookings
20000 --visitors 1000`, four API processes and the worker as
`perf/docker-compose.perf.yml`, k6 1.3.0 running the scenario
unchanged), `fa1132e` (the last green run, 2026-10-07) and `20d3dc0` cost
the same per request within the noise: 13.05 against 13.08 statements
per poll (`pg_stat_statements` with the counting function's own), API
CPU per poll 6.6 against 7.6 ms (2,000 sequential polls, one process),
Postgres CPU per request 4.5 against 4.3 ms, 3.1 pool checkouts per
request, the same lock waits (rate-limit rows, the inbound lane's claim
lock), the worker's CPU and statements per answer (99 ms, 247). H6's
scoped transactions add 0.3–1 ms of Python per poll at most. The
worker's inbound backlog of 36–41 s is not new either: the scenario
writes about 8.3 messages a second against eight inbound threads of
about a second each, and the green run's log picks messages up 46–48 s
late too. The thresholds time the poll and the `202` of a message, not
the answer.

**The cause.** The runner had no headroom left for what a poll cost: on
a saturated 4 vCPU runner (k6, Postgres, four API processes and the
worker) every poll made 8 round trips (13 statements) and wrote two rows
every poll of the platform shares, its business's and
`widget-poll:platform` in `rate_limit_buckets`. A poll holds those row
locks only while its counting statement runs (1135), but a holder that
loses its CPU mid-statement on a saturated machine holds every other
poll behind it: the p90 at 145 ms and maxima of seconds. Under the k6
load the sampled connections waited on those rows' locks
(`Lock:transactionid`, below), and only there among the poll's
statements.

**What changed (2026-10-22).**

- *Leased shared counters* (`RateLimitCounter.lease_size`,
  `RateLimitLeases`, `workshop.lease_requests_within_limit` of migration
  1215). A poll's business and platform counters are taken in leases: a
  process counts 1% of the limit (60 and 600 polls) on the shared row in
  one statement, as many as the sliding window still holds, and admits
  polls from them without touching the row; the poll that finds less than
  a fifth left tops the lease up ahead while the others go on, and a poll
  refused by its visitor or network gives its units back. The visitor
  and network are still counted per poll, in one statement on two rows
  nobody else writes. Messages, uploads, handoffs and ratings count all
  four counters per request as before.
- *One read in one round trip* (`WidgetPollReadAdapterContract`,
  `PostgresWidgetPollReadAdapter`, `workshop.read_widget_poll` of
  migration 1216). One statement reads the business's allowed websites,
  the visitor's conversations, the positions of their ten newest
  messages and, in full, only the messages after the cursor; its scope's
  `set_config` and the statement go as one pipeline (`fetch_in_scope`:
  the extended protocol's implicit transaction ends at the sync, and the
  scope with it). The statement lives in a PL/pgSQL function because the
  application sends no prepared statements (transaction poolers drop
  them): sent as plain SQL it was planned on every poll, about 0.5 ms of
  Postgres CPU, more than it took to run; the function's plan is kept
  per session. Without Postgres the use case reads through its
  repositories as before.
- *The origin check reads with it.* The poll checks its page against the
  allowed websites itself, from that statement (403 as before, now after
  the rate limit), instead of a transaction of its own in the route.
- *The counting function switches its scope by expressions.* 1215
  replaces `workshop.count_request_within_limits` with the same function
  whose two `set_config` calls are PL/pgSQL assignments instead of
  `perform` queries: two executor runs less per counted request, same
  answers (`test_rate_limit_parity.py`, `test_rate_limit_concurrency.py`).

A poll is now 2 round trips and 3 statements sent (the visitor and
network count; the scope and the read), whether it finds nothing or a
new answer; a lease top-up adds one per 60 polls of a business and per
600 of the platform in each process, the open chat's channel read one
per 10 s (`OpenChatMemory`, unchanged).

**Guarantees kept, and where they are tested.**

- One visitor and one network are held to 60 and 300 polls a minute
  across every API process, exactly (`test_widget_poll_limits.py`: four
  registries over one set of counters; `test_widget_polling_cost.py`:
  the 61st poll gets 429 with the same Retry-After).
- A business and the platform never pass 6,000 and 60,000 polls a minute
  either: every unit is counted before it admits a poll, so leases bind
  early by at most a lease and a fifth per process, never late
  (`test_rate_limit_leases.py`: 32 threads over four pools behind a
  barrier, drained to exactly the limit; in-memory and Postgres grant
  alike, refused leases leave no bucket and keep the caller's scope;
  `test_rate_limit_lease_book.py` for window edges and give-backs).
- A refused poll counts nowhere: its leased units go back, its
  per-request counts are taken back by the counting function as before.
- Every cursor gets the whole chat's answer through the one statement
  too (`test_widget_poll_window.py`, random chats with ties, several and
  sandbox conversations, other visitors), and polls racing the answers
  of their chat see each once, in order (`test_widget_poll_race.py`,
  four widgets and a writer behind a barrier).
- Row-level security binds the statement in the ambient scope, every
  table is also filtered by the business asked for, another business's
  scope reads nothing, no scope is refused, and the pipelined scope ends
  with the read (`test_widget_poll_reads.py`); a foreign website gets
  403 through both read paths.
- `test_request_statement_counts.py` holds the poll to 2 round trips
  (was 8), `test_widget_poll_statements.py` a poll with nothing new and
  one with a new answer to 2 round trips and 3 statements, and five
  polls in a row to 10.

**With wave 20's two database roles (merged 2026-10-23).** The
migrations are 1215 and 1216 (1194 and 1195 on the branch). The poll's
count and its lease top-ups run on the platform pool: only
`workshop_platform` may call `count_request_within_limits` and
`lease_requests_within_limit`, and the lease sets no `app.bypass_rls`
(no policy reads it since 1200). The read runs on the tenant pool in the
business's scope, where the tenant role's `tenant_isolation` policies
bind `read_widget_poll`; PUBLIC may call none of the three
(`test_poll_functions_on_two_roles.py`). Counted over both pools together
(`traced_together`), a poll stays 2 round trips and 3 statements, with
nothing new and with a new answer: the 8 of wave 20 fell to 2 in
`test_request_statement_counts.py`.

**Measured.** The counts come from libpq's trace and
`pg_stat_statements` and do not depend on the machine; the CPU and the
latencies were measured on a 4 vCPU machine that other jobs kept at a
load of 5–37, before (`395027c`) and after alternating, each from the
same seeded database (`seed-load --businesses 50 --messages 200000
--bookings 20000 --visitors 1000`, analysed).

One API process (production's 40 threads and 12 connections), 3,000
polls one after another per phase, three pairs (medians): "nothing new"
polls visitors with nothing after their cursor, "new answer" visitors
whose answer came after it (the k6 scenario's cursor never moves, so
after a visitor's first message every poll of it is one of these). API
CPU is the process's, Postgres CPU its connections' backends
(`/proc`); statements are `pg_stat_statements` calls per poll, the
counting function's and the read function's own included:

| Per poll | Nothing new, before | after | New answer, before | after |
| --- | ---: | ---: | ---: | ---: |
| Round trips (trace) | 8 | 2 | 9 | 2 |
| Statements sent (trace) | 8 | 3 | 9 | 3 |
| Statements, top level | 10.07 | 3.13 | 11.03 | 3.06 |
| Statements, with functions' own | 13.07 | 5.17 | 14.03 | 5.11 |
| API CPU | 6.37 ms | 4.01 ms | 6.86 ms | 4.86 ms |
| Postgres CPU | 3.34 ms | 1.49 ms | 2.88 ms | 1.32 ms |
| API and Postgres CPU | 9.71 ms | 5.50 ms | 9.74 ms | 6.18 ms |
| Wall time, one after another | 15.2 ms | 7.1 ms | 14.1 ms | 7.8 ms |

Postgres CPU fell by 54–55%, the API's by 29–37% (a request's HTTP and
framework work, about 0.8 ms for `/healthz` here, did not change), the
two together by 37–43%; the statements by 60–64%. Postgres had spent
part of it planning: the application sends no prepared statements, so
each of the four reads was planned on every poll (0.1–0.2 ms each);
the read function's plan is kept per session. The counting statement
averaged 1.06 ms for four keys before and 0.79 ms for two after.

**Under k6.** `widget_polling.js` unchanged (1,000 visitors, 5 minutes,
the scripted model at 800 ms) against that stack and seeded database,
before and after alternating, with the stack at `nice -10` from the
third pair on so the other jobs took less of its CPU (their load was 6–19
when each run started). This machine is much slower than the CI runner
for the scenario (before, the poll median was 0.5–0.9 s against CI's
35 ms): every run saturated its four vCPUs, so these runs compare the two
versions under overload, not against the 150 ms gate. Milliseconds;
"restarts" are API processes uvicorn killed and replaced; lock waits are
`pg_stat_activity` samples (every 0.5 s) of a statement waiting on a
rate-limit row.

| Pair | Version | Restarts | Poll p50 | p90 | p95 | Message p95 | Requests | Lock waits |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | before | 3 | 893 | 3,375 | 4,987 | 7,020 | 56,536 | 2 |
| 1 | after | 4 | 528 | 2,587 | 7,459 | 7,065 | 47,891 (1.1% failed) | 0 |
| 2 | before | 0 | 722 | 2,010 | 2,767 | 3,158 | 61,394 | 9 |
| 2 | after | 4 | 894 | 3,621 | 5,387 | 7,072 | 55,871 | 0 |
| 3 | before | 1 | 692 | 2,461 | 3,568 | 5,329 | 59,864 | 38 |
| 3 | after | 5 | 364 | 2,454 | 7,033 | 4,951 | 47,632 (2.1% failed) | 0 |
| 4 | before | 0 | 524 | 1,733 | 2,435 | 2,583 | 63,794 | 4 |
| 4 | after | 1 | 189 | 1,094 | 1,596 | 1,661 | 69,079 | 0 |
| 5 | before | 0 | 610 | 1,836 | 2,383 | 4,134 | 62,999 | 179 |
| 5 | after | 0 | 278 | 1,163 | 1,698 | 1,685 | 68,152 | 0 |
| 6 | after | 0 | 166 | 929 | 1,348 | 1,594 | 70,563 | 0 |

(Pair 6's "before" run lost k6 itself to the machine's memory limit.)
The rate-limit rows' lock waits are gone in every run. Where no process
or one was restarted (pairs 4 and 5), the poll median fell by 54–64% and
the p95 by 29–34%, and more polls got through (a visitor polls again
sooner). The runs with several restarts are the worst of both versions.

**The restarts: full garbage collections.** uvicorn replaces an API
process that does not answer its health check within 5 s. A probe thread
in each API process (harness only: it timed its own 50 ms sleeps and
`gc.callbacks`) showed what stops them: every stall over a second
coincided with a full (generation 2) collection, 1–5 s long under this
load in both versions (before up to 4.9 s, after up to 4.1 s), 8–10 of
them per process and run. An idle API process tracks 1.06 million
objects (the container's providers, the pydantic and FastAPI schemas),
and a full collection walks all of them: about 1 s on this machine at
rest. A replaced process imports for 10–25 s while the other three take
its visitors, so one restart often brought more. Restarts came more
often after the change here (17 in 7 runs, two of them 3-minute runs
under `py-spy`, against 5 in 7 before); why was not established, the
collections themselves were no longer after it. In one experiment
outside this change, freezing the startup heap 40 s after start
(`gc.collect(); gc.freeze()`) gave the version after it a poll median of
74 ms and a p95 of 812 ms with no restart (that run was stopped 15 s
early for memory); collections still took 0.3–2 s there. Garbage
collection pauses are the next lever on this scenario's tail; whether
they weigh on the CI runner's p95 (its maxima were 3–3.7 s) these local
runs cannot tell.

### Garbage collection: the startup heap frozen after warm-up (2026-10-26)

**What changed.** Every API process and every worker collects once and
freezes what is alive (`gc.collect()`, `gc.freeze()`) after it has warmed
up and before its first request or job (`StartupHeapTuner`,
`settle_startup_heap`): the API at the end of its lifespan's startup (the
container and its routers, the catalogs, the role checks, the platform
bot, the trace flush, the watchdog and an embedded worker started), the
worker after its container, the reply guard's CLDR data and its metrics
server. Frozen objects stay where they are, but no collection walks them
again; a process that stops gives them back. `GC_FREEZE_AFTER_WARMUP=false`
turns it off; `GC_THRESHOLDS` sets the collector's thresholds (empty:
Python's 2000, 10, 10; see below). Each process times its collections with
`gc.callbacks` into `workshop_gc_pause_seconds` by generation and reports
`workshop_gc_frozen_objects` (`docs/operations/observability.md`; the
dashboard graphs both). The callback only queues the pause: a collection
can start while a thread holds a metric's lock, so a thread of its own
observes the queued pauses every 5 s.

**The startup heap.** An API process froze 1,406,476–1,406,502 objects, a
worker 1,317,814–1,317,843 (1.06 million were counted on 2026-10-20; the
code has grown since). Collecting and freezing them took 0.8–1.8 s of an API
process's startup and 0.7–1.4 s of the worker's, before either serves (a
process uvicorn replaces pays it again). Resident memory after a run was
the same with and without the freeze (0.50–0.52 GB per API process).

**How it was measured.** On 2026-10-26, on a 4 vCPU, 16 GB machine shared
with other jobs (load average 3.8–21 during the runs, noted per run).
Postgres 16 with its defaults on the same machine, the migrations and
`seed-load --businesses 50 --messages 200000 --bookings 20000 --visitors
1000` (93 s) into a template database; every run started from a fresh copy
of it. The API ran as `workshop api` runs it in
`perf/docker-compose.perf.yml` (uvicorn, four processes, 40 threads and
10 + 4 connections each), the worker as that file sets it (20 threads,
14 + 4 connections, 12 model calls), both on the host with the scripted
model at 800 ms and no route to the providers; k6 1.3.0 (that file's
`grafana/k6:1.3.0` image, on the host's network) ran `widget_polling.js`
unchanged: 1,000 visitors for 5 minutes. Freeze off and on alternated,
five pairs. The collections are the difference of
`workshop_gc_pause_seconds` scraped just before and after each k6 run (the
API's `/metrics` sums its four processes); the histogram's buckets bound
the longest pause.

Collections per run (mean of five runs) and their pauses, Python's
thresholds:

| Process, generation | Off: per run | mean pause | longest | On: per run | mean pause | longest |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| API (four processes), 0 | 3,311 | 2.3 ms | 100–250 ms | 3,275 | 2.6 ms | 100–250 ms |
| API, 1 | 302 | 8.8 ms | 100–250 ms | 296 | 9.3 ms | 100–250 ms |
| API, 2 (full) | 5.4 | 1,130 ms | 2.5–5 s | 12.6 | 29 ms | 100–250 ms |
| Worker, 0 | 806 | 1.3 ms | 100–250 ms | 811 | 1.4 ms | 100–250 ms |
| Worker, 1 | 73 | 3.2 ms | 50–100 ms | 73 | 3.5 ms | 25–50 ms |
| Worker, 2 (full) | 1.2 | 837 ms | 1–2.5 s | 3.8 | 6.3 ms | 10–25 ms |
| API time in collections per run | 16.3 s | | | 11.7 s | | |
| Worker time in collections per run | 2.3 s | | | 1.4 s | | |

Off, every one of the API's 27 full collections stopped its process for
more than 250 ms (13 for more than a second, up to 2.5–5 s when the
machine was busiest), and so did the worker's 6. On, none of the 63 full
collections of the API passed 250 ms (one passed 100 ms) and none of the
worker's 19 passed 25 ms. They came more often (12.6 per run against 5.4),
each walking only what the process kept since it warmed up. The younger
generations did not change: their pauses follow the machine's load.

The k6 runs (milliseconds; load average at the run's start and end; p99
was recorded from the third pair's second run on):

| Pair | Freeze | Load | Poll p50 | Poll p95 | Poll p99 | Poll max | Message p50 | Message p95 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | off | 3.8 → 6.1 | 7.1 | 24.6 | — | 981 | 22.5 | 66 |
| 1 | on | 5.7 → 6.4 | 10.8 | 76.3 | — | 582 | 32.2 | 158 |
| 2 | off | 6.0 → 4.9 | 7.3 | 31.5 | — | 1,040 | 25.6 | 168 |
| 2 | on | 4.5 → 4.8 | 7.4 | 47.5 | — | 724 | 23.0 | 127 |
| 3 | off | 4.5 → 6.6 | 8.9 | 82.4 | — | 1,914 | 26.6 | 175 |
| 3 | on | 6.2 → 5.1 | 9.8 | 49.0 | 123 | 618 | 29.0 | 107 |
| 4 | off | 3.9 → 10.6 | 13.2 | 221.3 | 704 | 2,837 | 36.8 | 326 |
| 4 | on | 9.8 → 12.4 | 24.1 | 266.7 | 488 | 931 | 52.9 | 447 |
| 5 | off | 11.7 → 14.4 | 16.4 | 365.2 | 899 | 3,263 | 42.4 | 560 |
| 5 | on | 13.4 → 8.5 | 9.3 | 50.8 | 129 | 375 | 27.1 | 108 |

Every run answered every request (75,900–77,200; none failed) and no API
process was restarted: this machine is much faster for the scenario than
the one of 2026-10-20 (poll median 7–24 ms against 0.2–0.9 s). Medians of
the five runs, off against on: poll p50 8.9 and 9.8 ms, p95 82 and 51 ms,
maximum 1,914 and 618 ms, message p95 175 and 127 ms. The longest poll of
each run without the freeze (0.98–3.3 s) was about as long as that run's
longest full collection; with it, the longest of the five runs was
0.93 s. The p50 and p95 moved with the machine's load and with how the
1,000 kept-alive connections fell on the four processes (the busiest took
27–34% of the API's CPU) more than with the freeze: in pairs 1 and 2 the
run without it had the better p95, in pairs 3 and 5 the run with it. The
scenario's own thresholds failed in three runs, all with the load above
10 (pair 4 both, pair 5 off); the fourth such run (pair 5 on) met them.

**Thresholds.** Two more pairs, both with the freeze, alternated Python's
thresholds with `GC_THRESHOLDS=10000,10,10`:

| Run | Load | Poll p50 / p95 / max | API collections (0 / 1 / 2) | Young pause mean (longest) | API time in collections |
| --- | --- | ---: | ---: | ---: | ---: |
| 1, Python's | 7.9 → 17.4 | 68 / 546 / 1,784 ms | 3,672 / 332 / 19 | 6.8 ms (100–250 ms) | 34.0 s |
| 1, 10000,10,10 | 16.1 → 9.3 | 9.9 / 82 / 561 ms | 578 / 51 / 0 | 14.7 ms (100–250 ms) | 9.4 s |
| 2, Python's | 8.2 → 11.1 | 8.3 / 75 / 634 ms | 3,237 / 293 / 11 | 2.1 ms (50–100 ms) | 9.4 s |
| 2, 10000,10,10 | 10.3 → 21.0 | 12.4 / 287 / 1,346 ms | 582 / 51 / 0 | 20.3 ms (250–500 ms) | 13.1 s |

A young threshold of 10,000 cut the API's collections by five sixths and
the worker's by 96% (33 and 29 young ones a run instead of 680–800), and
no full collection ran within five minutes; but a young collection then
took 15–20 ms on average instead of 2–7 ms (up to 250–500 ms), and the
time spent in collections did not fall (9.4 and 13.1 s against 9.4 s in
the second pair and 11.7 s in the five runs above). The latencies followed
the machine's load: in each pair the run whose load rose to 17–21 was the
slow one. Not clearly better: `GC_THRESHOLDS` stays empty, Python's
thresholds.

**What remains.** The weekly run on GitHub's runner shows whether the
CI's poll maxima of 3–3.7 s were these collections; its p95 is set by
the runner's load as much as here. The freeze costs about a second of
each process's startup.

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
  stayed at p50 87 ms, p95 1.4 s. Production runs two customer workers
  ("Worker roles" below). Raise the `inbound` concurrency (within
  `LLM_MAX_CONCURRENCY` and `DB_POOL_SIZE`: a turn holds a connection
  while it runs; mind the provider's rate limits) or add customer
  workers (mind the connection budget) when the queue's wait grows (the
  admin system page,
  `/admin/system`: the `inbound` lane's oldest wait; the
  `inbound_backlog` alert pages above 120 s, `docs/operations/slo.md`).
- **Database connections.** Every process keeps up to `DB_POOL_SIZE`
  connections of the tenant role (half of `THREADPOOL_SIZE` unless set)
  and `DB_PLATFORM_POOL_SIZE` of the platform role, and closes those idle
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

## Worker roles

Workers serve lanes (`WORKER_LANES`, a comma list; empty means every
lane, as in development and docker compose). `render.yaml` runs two
roles, so no batch job can take down or starve the process that answers
customers:

| Service | Instances, plan | Lanes | Shared periodic jobs | Sizing |
| --- | --- | --- | --- | --- |
| `workshop-worker` | 2 x `starter` | `inbound`, `outbound` (`ops` joins with the release that opens the gate `ops_lane`) | `send_booking_reminders` (outbound), `sweep_stale_inbound_events` (inbound) | 12 lane threads (`inbound=8,outbound=4`, the defaults; 13 with `ops=1`), `DB_POOL_SIZE` 14 and `DB_PLATFORM_POOL_SIZE` 4, `THREADPOOL_SIZE` 20, `LLM_MAX_CONCURRENCY` 12 |
| `workshop-batch-worker` | 1 x `standard` (2 GB) | `default`, `autotests` | every other one (exports, website imports, summaries, digests and reports, the nightly jobs) | `default=4,autotests=2`, `DB_POOL_SIZE` 8 and `DB_PLATFORM_POOL_SIZE` 4, `THREADPOOL_SIZE` 12, `LLM_MAX_CONCURRENCY` 6 |

- A periodic job belongs to a lane (`PeriodicJobSpec.lane`, `default`
  unless set); a worker runs the shared ones of its lanes, still once
  per period across all workers (`periodic_job_runs`), and every worker
  runs the process-local ones (the model-call trace flush). The reaper
  and the lease heartbeat run on every worker.
- Two customer workers: one can die or deploy while the other answers
  ("When a worker dies" below). A third adds 2 x 19 connections at a
  deploy.
- `tests/platform/test_worker_roles.py` keeps it so: every lane is
  served by exactly one role in both Blueprints (a lane nobody serves
  would never run), customer replies run on at least two instances, each
  worker's pool holds its lane threads plus the periodic thread and the
  heartbeat, and its `LLM_MAX_CONCURRENCY` covers its `inbound` threads.
- Sizing a role: `DB_POOL_SIZE` >= its lane threads + 2;
  `LLM_MAX_CONCURRENCY` >= its `inbound` threads (a turn waits for a
  place before it takes a connection); `THREADPOOL_SIZE` above the pool.
  Then check the connection budget below.

## Bulkheads: one provider cannot take the outbound lane

A provider that hangs holds a thread for its whole read timeout (10 s, 3 s
to connect; SMTP the same). Without a limit four slow WhatsApp sends would
take all four `outbound` threads of a worker, and Telegram replies, staff
notifications and the platform alerts would wait behind them.

- **Per-provider slots.** Each worker gives every provider at most half of
  its `outbound` threads (`OutboundBulkheadFacilitator`, 2 of the default
  4, at least 1). A send that finds its provider's slots taken does not
  wait: the job comes back in about 4 s, the message keeps its attempts
  and its place (same serial key). Meta hanging therefore costs 2 threads;
  the other 2 keep sending through Telegram, the platform bot, Twilio and
  SMTP.
- **Circuit breakers.** Five failures of a provider within 60 s open its
  circuit in that process: sends fail at once without a call and the
  outbox retries after the circuit's 30 s (runbook
  [provider-circuits](runbooks/provider-circuits.md)). A brownout costs
  five timeouts per worker, not one per message.
- **The ops lane.** `send_platform_alert` jobs get their own lane with one
  thread per worker (`ops=1`, the default), to be served by the customer
  workers. It is behind the release gate `ops_lane` (the release before
  cannot read the lane): until the next release opens it, alerts use
  `outbound`, where the bulkheads leave them two threads, and no
  Blueprint names `ops` in `WORKER_LANES` or `WORKER_LANE_CONCURRENCY`
  (the release before refuses the value at startup, and a rollback keeps
  the environment). The release that opens the gate adds `ops` to
  `workshop-worker`'s `WORKER_LANES`.
- Measured in `tests/resilience/test_send_bulkheads.py`: with Meta hanging
  10 s and the production lanes, a Telegram reply and a platform alert go
  out within 2 s, and no outbox row is lost or sent twice.

## When a worker dies

- **Leases.** A claimed job is leased for 120 s; the heartbeat renews
  the leases of running jobs every 30 s. The reaper releases the jobs of
  a worker that stopped beating: on every tick, and between ticks as
  often as the worker's quickest lane polls (every
  `WORKER_INBOUND_POLL_SECONDS`, 2 s, on the customer workers); it wakes
  the lanes of the jobs it put back, so another worker claims them at
  once.
- **The customer's message.** The inbox event remembers the job that
  took it (`holder_job_id`). The queue hands a job out again only after
  its earlier attempt is over, so that job's next attempt takes the
  message over at once instead of waiting out the 180 s processing
  lease; any other job still waits for it. The ids of the customer's
  message and of the reply are fixed in the inbox, a reply already
  stored is sent instead of asked again, and the outbox keeps one row
  per reply: the customer gets one answer.
  `tests/storage/test_worker_kill.py` runs two customer workers and an
  API on Postgres, `kill -9`s the worker in the middle of a Telegram
  customer's turn and checks the other answers within the lease plus
  5 s with exactly one outbound row, sent once (with a 6 s lease it
  answered 7.7 s after the kill); in production expect about 2 minutes.
- **Deploys.** On SIGTERM running jobs get 25 s to finish; the rest are
  handed back (due at once, not counted as an attempt or a lost lease),
  so a deploy neither delays a customer by a lease nor looks like a
  crash.
- **Poison jobs.** Every lost lease is counted on the job
  (`lost_leases`, reset when an attempt settles). A job whose worker
  died with it twice in a row is DEAD with the reason `process_died`
  instead of a third attempt: an error report names it and the
  `dead_jobs` alert pages (`runbooks/stuck-worker.md`). The system page
  shows the reason of every dead letter; Retry resets the count.
- **Memory per job.** Every finished job logs
  `Job <name> <outcome> in <n> ms; RSS <a> MB before, <b> MB after` with
  the fields `duration_ms`, `outcome`, `rss_before_mb` and `rss_after_mb`
  (the process's resident memory from `/proc/self/statm`; absent where
  there is none). Search the batch worker's logs for the largest
  `rss_after_mb` minus `rss_before_mb` to find a job that reads too much.

## Memory of batch jobs

- **Full business exports** never hold a collection: the ZIP is written
  into a temporary file, every collection streamed in keyset pages of
  1,000 (first-write order on the `(business_id, created_at,
  row_sequence)` index) through incremental JSON and CSV writers, then
  sealed in 1 MiB segments (AES-256-GCM, format AWX2) and uploaded in
  8 MiB parts (S3 multipart). Exporting 50,000 messages peaks at about
  14 MB of Python allocations (`tests/exports/test_bounded_export.py`
  fails above 64 MB).
- **Their download** (in the API) never holds the archive either: the
  sealed archive is read from the bucket in ranges of four segments as
  the response asks for pieces, each segment opened and checked on its
  own and sent as a 1 MiB piece (a streamed response). Downloading a
  48 MiB archive peaks at about 8 MB of Python allocations
  (`tests/exports/test_bounded_download.py` fails above 12 MB).
- **Admin metrics** walk every business in batches of 200 and keep only
  each one's roster (members, country, niche, start), not its profile.
- **Topic grouping** reads at most 200 conversations and 100 unanswered
  questions per business, walking businesses in batches.
- **Invoice PDFs** render one invoice per job (WeasyPrint, bounded by the
  invoice), but on the `outbound` lane, so on the customer workers
  ("Known limits").

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
  threads at once. A job queued for later within 10 minutes (a burst of
  customer messages answered once the customer is quiet, a retry after
  its backoff) notifies `<lane>@<run_at in µs>`: the worker arms a timer
  (`JobWakeupTimer`, one thread per listening worker) and wakes the lane
  when the job is due, not at its next poll; a worker of an older release
  ignores such a notification and its poll finds the job.
- **Customer messages.** Each inbox event records `queue_to_claim_ms`,
  from being stored to being taken for an answer (the grouping wait
  included), and the claim logs it with the burst's size ("Customer
  messages taken to answer"). A finished message (over 12 characters,
  ending in `.`, `?` or `!`) is due at once: expect tens of
  milliseconds. A short fragment waits `MESSAGE_COALESCE_SECONDS` (3;
  1.5 s on Telegram) for the rest of the thought.
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

Production's database is Render's `pro-8gb` Postgres: 200 connections
(plans below 8 GB accept 100, 16 GB 400, 32 GB 500). The worst moment is
a deploy: Render starts the new instances of every service before it
stops the old ones, while the backup may run and the migration runs
before. `tests/platform/test_connection_budget.py` reads every Blueprint
and checks, per role,

```
  2 x API instances             x (DB_POOL_SIZE + DB_PLATFORM_POOL_SIZE + 1 LISTEN)
+ 2 x customer worker instances x (DB_POOL_SIZE + DB_PLATFORM_POOL_SIZE + 1 LISTEN)
+ 2 x batch worker instances    x (DB_POOL_SIZE + DB_PLATFORM_POOL_SIZE + 1 LISTEN)
+ backup 2 + migrate 1 + reserved 5        <=   the plan's limit
```

(reserved: Postgres's three superuser connections, an operator's psql and
Render's own checks). Every process has two pools since migration 1200
(`docs/operations/deploys.md`, "Database roles"): `DB_POOL_SIZE`
connections of the tenant role, which serve everything in a business's
scope, and `DB_PLATFORM_POOL_SIZE` of the platform role (sign-in, the job
queue's claims, rate limits, platform-wide work: short statements, so a
smaller pool; default a quarter of `DB_POOL_SIZE`, at least 2).
Production (`render.yaml`): 2 x 2 x (10 + 4 + 1) = 60 for the API,
2 x 2 x (14 + 4 + 1) = 76 for the customer workers, 2 x 1 x (8 + 4 + 1)
= 26 for the batch worker, 2 + 1 + 5: 170 of 200. The tenant pools gave
up two connections each (12 to 10, 16 to 14, 10 to 8) for the platform
pools, so the work a process can run at once stays about the same while
the second pool fits; there is no room left for a third customer worker
without one of the routes below. Staging (one API, one worker serving
every lane, `basic-256mb`): 2 x (10 + 4 + 1) + 2 x (19 + 4 + 1) + 8 = 86
of 100. The defaults (64 threads, 32 + 8 connections) would not fit: a
Blueprint without `DB_POOL_SIZE` on any service fails the test, and so
does a worker without `DB_PLATFORM_POOL_SIZE`.

The worker roles need 170 connections at a deploy (150 before the
second pool), more than the 100 of
the plan before (`basic-256mb`); of the routes below the larger plan won: PgBouncer in session mode multiplexes
nothing a busy pool holds (every customer turn keeps its connection for
the turn's advisory lock), adds a service to run and monitor, and the
Blueprint cannot hand its address to the others the way it hands the
database's. When more is needed again, pick one route and update the
Blueprint and the test together:

- **A larger database plan.** Add its connection limit (Render, "Postgres
  connection limits") to `PLAN_CONNECTION_LIMITS` in
  `tests/platform/connection_budget.py`.
- **PgBouncer in front.** Run PgBouncer as a private service in session
  mode with `max_db_connections` below the plan's limit minus the
  reserve, and point `DATABASE_URL` of the API and the workers at it: a
  deploy's peak then waits in PgBouncer instead of failing with "too many
  clients", and idle pools (closed after 300 s) free their server
  connections. Transaction mode is not enough: a customer turn holds a
  session advisory lock on its connection
  (`app/adapters/locks/postgres_advisory_lock_adapter.py`), and LISTEN
  needs a session (`LIVE_EVENTS_DATABASE_URL` then names the direct
  address). Count PgBouncer's limit, not the pools, in the test.
- **Smaller pools.** Lower `DB_POOL_SIZE` or `DB_PLATFORM_POOL_SIZE`
  per process; requests queue for a connection a little longer, and
  readiness stays green while they do.

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
- The admin metrics page walks every business in batches of 200 and
  keeps each one's roster for the funnel (a few hundred bytes each), but
  still holds every product event of the period: fine for thousands.
- Invoice and receipt PDFs render on the `outbound` lane (their e-mails
  go through the outbox), so on the customer workers: bounded by one
  invoice, but a slow WeasyPrint run holds an outbound thread. Moving
  billing documents to a batch lane is the next step.
- Periodic job runs are not counted like queued jobs: a periodic job
  that kills its worker runs again in its next period.
- The customer list and the knowledge list page in the database
  (migration 1122); the customer search finds exact names, phones and ids
  through indexes and walks at most 500 customers for a part of a name.
- A widget poll reads where the visitor's ten newest messages stand and
  only the messages after its cursor, in one statement; only a backlog
  longer than that, an unknown cursor or none reads the visitor's whole
  chat (bounded by one visitor's chat, not by the business).
- A widget switched off still answers polls for up to 10 s in every API
  process (`OpenChatMemory`); its messages are refused at once.
- Widget polls take their business's and the platform's rate-limit
  counters in leases of 1% of the limit per process, topped up when a
  fifth is left (migration 1215): with N API processes those two limits
  may refuse up to 1.2 × N % early, never late. Messages, uploads,
  handoffs and ratings still count every request in all four counters.
- The startup heap each API and worker process freezes after warm-up
  (`GC_FREEZE_AFTER_WARMUP`) is never searched for cycles again: frozen
  objects freed by their reference counts go as before, but a cycle among
  them that turns into garbage stays until the process stops. They are
  the container, the schemas and the routes, kept for the process's
  lifetime anyway.
- Seeding the full dataset took 21 minutes locally (the demo part of each
  business dominates); the weekly budgets job allows two hours.
- The scripted model answers every message with one sentence; a
  conversation the engine hands to staff afterwards gets no model call,
  so widget messages of such visitors measure storage, not the model.
