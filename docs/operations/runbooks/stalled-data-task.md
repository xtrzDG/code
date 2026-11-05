# Stalled data task: rows of an older release not migrated or indexed

**Alert:** `backfill_stalled` (SEV3): a post-deploy data task is not done
24 hours after it became due (`ops/alerts/backfill_stalled.yaml`). It
fires again at most once per cooldown and resolves once the task is done.

**Other signals:** the "Data after deploys" card on `/admin/system` shows
the task as failed, stalled or waiting; `GET /readyz` reports
`checks.data_tasks.open` above 0 for a long time; the deploy-smoke workflow
refuses to promote the next release ("production still has open data
tasks"); the cabinet's customer or knowledge list says it is still
indexing.

## What runs by itself

After every deploy, the batch worker's `run_data_tasks` job (every 5
minutes, `docs/operations/deploys.md`, "Data tasks after a deploy"):

1. waits until no worker of another release has beaten for 15 minutes
   (the release overlap is over);
2. rewrites documents of older schema versions, collection by collection
   (`migrate_documents:<collection>`);
3. fills the trigger-kept lookup columns of older rows
   (`backfill_lookup:<collection>.<field>`),

in keyset batches of 5,000 rows, one short transaction each, storing the
progress after every batch. A run stops starting batches after 4 minutes;
the next run goes on.

## Check

Open `/admin/system`, card "Data after deploys". For the stalled task:

- **Waiting for the release overlap**: the card names the other release
  that still beats. Look at the worker pulses card: a worker of the old
  release that never stopped (a stuck instance, a second worker service on
  an old commit). Stop it on Render; the tasks start 15 minutes after its
  last pulse.
- **Batches fail** (`failure_count` and the last error): a row stays
  locked for more than 5 seconds (a long transaction:
  `select pid, xact_start, query from pg_stat_activity where xact_start <
  now() - interval '1 minute'`), the database is down or full. Each run
  tries the same batch again; once the cause is gone it moves on.
- **Failed** (rows that could not be upgraded): the card lists the first
  document keys. Read one stored row
  (`select document from workshop.<collection> where document_key = '…'`)
  and its version's golden fixture; usually an upcaster misses a case.
  Fix the upcaster in a release: a failed task walks again when the next
  release runs, or press "Run again" on the card after fixing the rows.

## Mitigate

Nothing is lost while a task waits: reads upcast old documents, and the
trigger fills the columns of every row written since the migration. Lists
that page by an unfilled column show "still indexing" and may miss older
rows. The deploy guard keeps production on the current release until the
tasks are done; promote by hand only when the open task cannot matter for
the next release (`git push origin <commit>:release`, deploys.md).

## Fix

The same work by hand, as before the automation, from the API's Render
Shell (both are idempotent and resumable):

```
workshop migrate-documents --collection <collection>
workshop backfill-lookup --collection <collection> --field <field>
```

The runner sees what they did on its next walk (the rows are current and
the columns filled), finishes quickly and marks the task done.

## Afterwards

If an upcaster missed a case, add a golden fixture of the row's shape
(`tests/storage/golden/`) so the evolution test covers it.
