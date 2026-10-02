# 0004. Background work in a Python worker on a queue in Postgres

- Status: Accepted
- Date: 2026-10-02

## Context

The product sends reminders, ends trials, charges and retries payments,
plays autotest scenarios against the model, purges recordings and syncs
calendars. The original specification suggested a Node worker with
pg-boss. Running a second language would duplicate the use cases, the
typed primitives and the tenant isolation that the API already has.

## Decision

- Background work runs in a Python worker (`app/worker_main.py`,
  `app/gateways/worker/`) that uses the same containers and use cases as
  the API.
- Periodic jobs are listed in `app/containers/gateways.py`; one-off work
  is queued as documents in Postgres (`QueuedJobDocument`) with attempts,
  backoff and an error text, so a crash or deploy loses no job.
- Jobs that belong to a business run inside that business's storage scope
  (row-level security), like API requests.
- In development without Postgres the same worker runs as a thread inside
  the API process (`EMBEDDED_WORKER`), so the whole product starts with one
  command.

## Consequences

- One language, one set of rules, one place to fix a bug.
- Postgres is also the queue: no extra infrastructure, transactional
  enqueueing with the data it concerns, but throughput is bounded by the
  database. Several worker instances need leased claims so a job runs once;
  that is the planned evolution of this queue.
- Long jobs (autotests) run off the request path; the API answers at once
  and the cabinet polls their state.
