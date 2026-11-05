# 0007. Online-safe migrations and trigger-filled lookup columns

- Status: Accepted
- Date: 2026-10-22

## Context

Render runs `workshop migrate` as the `preDeployCommand` while the previous
release keeps serving and writing, and two releases run side by side during
every deploy and after a rollback. The first migrations were written for an
empty database: stored generated columns for every lookup field (a full
table rewrite under ACCESS EXCLUSIVE), indexes built without
`CONCURRENTLY`, data fixed with one `UPDATE` over the whole table. On a few
hundred thousand rows each of those stalls the live writes behind one lock
for as long as the statement runs: webhooks time out, providers redeliver,
customers wait.

The lookup columns themselves cannot go away. Every table has forced
row-level security, Postgres evaluates the policy before any condition that
is not leakproof, and `document ->> 'field' = $1` is not, so an expression
index on the JSON is never used. Repositories therefore query plain columns
(`doc_<field>`) declared in the lookup catalog.

## Decision

- **Bounded locks and retries.** Every migration statement waits at most
  5 s for a lock (`lock_timeout`); a file that timed out or lost a deadlock
  is rolled back and retried with jittered exponential backoff, five times,
  then the deploy fails with nothing of that file recorded. A file is one
  transaction; concurrent runners serialize on an advisory lock asked for
  outside any transaction.
- **No-transaction files** (`-- workshop:no-transaction`) hold the
  statements that cannot run in a transaction, `CREATE INDEX CONCURRENTLY
  IF NOT EXISTS` above all; the runner drops an INVALID index left by a
  failed build before each try, and every statement in such a file is
  idempotent.
- **The online-safety lint.** From migration 1115 on, a statement on a table
  an earlier file created must not rewrite it, build an index without
  `CONCURRENTLY`, update or delete its rows, change a type, `SET NOT NULL`
  or add a constraint without `NOT VALID`
  (`tests/storage/test_migration_safety.py`; the exempt list of earlier
  files never grows). A writer-stall test applies a real migration and its
  backfill under four writing threads and requires every write to finish in
  under 2 s.
- **Trigger-filled lookup columns.** A lookup field on an existing table is
  a nullable column added with `workshop.add_lookup_column` and filled by
  the table's BEFORE INSERT/UPDATE trigger from the document
  (`workshop.fill_lookup_columns()`, which reads the columns from the
  catalog), backfilled after the deploy by `workshop backfill-lookup` in
  keyset batches of 5,000, then indexed `CONCURRENTLY` in a later file. The
  document stays the only source of truth.
- **Data changes outside the deploy.** Rows change only through batched
  commands after the deploy (`backfill-lookup`, `migrate-documents`) or the
  post-release data tasks the worker runs and the admin System page shows;
  the release gate of the next promotion waits for them.

## Consequences

- A deploy never stalls the live release's writes for longer than a lock
  wait, and a migration that cannot get its locks fails the deploy cleanly
  instead of queuing traffic behind it.
- A lookup column is usable only once its backfill reached the old rows: until
  then a page sorted by it skips them and a count misses them, so features
  that read a new column ship a release after the column
  (`docs/operations/deploys.md`).
- Schema changes take more steps (add, fill, backfill, index, and only then
  constrain), and the lint rejects shortcuts; the steps are documented in
  [`migrations/README.md`](../../migrations/README.md), whose rules this
  record summarizes.
