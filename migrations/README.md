# Database migrations

SQL migrations of the Postgres document storage (EU region). Applied in
version order by

```bash
DATABASE_URL=postgresql://... uv run python -m app.gateways.cli.migrate
DATABASE_URL=postgresql://... uv run python -m app.gateways.cli.migrate --dry-run
DATABASE_URL=postgresql://... uv run python -m app.gateways.cli.migrate --lock-timeout 10 --attempts 8
```

(`workshop migrate` in the image; Render runs it as `preDeployCommand`, while
the previous release still serves.) The runner records every applied file in
`workshop.schema_migrations` with a SHA-256 checksum and serializes concurrent
runners with a session advisory lock that a waiting runner asks for again and
again outside any transaction, so it is safe on every deploy and from several
instances at once.

- **Bounded lock waits.** Every statement waits at most `--lock-timeout`
  seconds (5) for a lock (`lock_timeout`), so a migration that needs a table
  the live release keeps busy never queues that table's writes behind it.
  A statement may run up to 30 minutes once it has its locks (an index
  build).
- **Retries.** A file that timed out on a lock, or lost a deadlock, is
  rolled back and tried again after a jittered pause (exponential from
  1 s, each drawn between half and all of it), `--attempts` times (5) in
  all; then the runner fails the deploy (exit 1) and nothing of that file
  is recorded.
- **A file is one transaction**: its statements and its record commit
  together, or not at all.
- **No-transaction files.** A file whose first lines hold the header
  `-- workshop:no-transaction` runs statement by statement outside a
  transaction, for `CREATE INDEX CONCURRENTLY IF NOT EXISTS`. Before each
  try the runner drops (concurrently) every INVALID index the file creates:
  a failed concurrent build leaves its half-built index behind, and
  `IF NOT EXISTS` would skip it forever. The file is recorded only after
  its last statement succeeded, so every statement in it must be
  idempotent (`if not exists`, `create or replace`): a failed try runs the
  file again from the top.

Rules:

- Name files `NNNN_snake_case_slug.sql` with the next free 4-digit version.
- Never edit an applied file: the runner refuses a changed checksum. Add a
  new migration instead.
- No transaction control (`BEGIN`, `COMMIT`). A statement that cannot run
  inside a transaction (`CREATE INDEX CONCURRENTLY`) goes into a
  no-transaction file, and only there.
- A new document collection is one line:
  `select workshop.create_document_collection('collection_name');` — it
  creates the table, its indexes and the row-level security policy (see
  `0001_document_collections.sql` for the design). Add the name to
  `app/utilities/storage/document_collection_catalog.py` as well.
- Migrations after 1114 are online-safe (below);
  `tests/storage/test_migration_safety.py` lints them.

## Online-safe migrations

Every file runs while the previous release serves and writes. Anything that
holds a lock on a busy table for longer than a moment stalls the live
writes behind it, so a statement on a table that an earlier file created
(and that may be big by now) must not:

- add a stored generated column (it rewrites the table under ACCESS
  EXCLUSIVE);
- build an index without `CONCURRENTLY` (writes wait for the whole build);
- `UPDATE`, `DELETE` or `INSERT ... SELECT` its rows (one long transaction
  that locks every row it touches): fill data with `workshop
  backfill-lookup`, `workshop migrate-documents` or another batched command
  after the deploy;
- change a column's type, `SET NOT NULL`, or add a constraint without
  `NOT VALID` (a rewrite or a full scan under a strong lock).

A table the same file creates is new and empty: anything goes for it in
that file. `tests/storage/migration_lint.py` reads every file after 1114 in
version order and reports these statements; files applied before the rule
(up to 1114) are on its exempt list, which never grows.
`tests/perf/test_migration_writer_stalls.py` (`-m perf`, `PERF_SCALE=medium`:
200,000 contacts and bookings) applies 1122 and its backfill under four
writer threads; the longest write must stay under 2 s (0.31 s measured).

**A lookup field on an existing table is a nullable column filled by a
BEFORE INSERT/UPDATE trigger, backfilled by
`workshop backfill-lookup --collection X --field Y --batch 5000` in keyset
batches outside the deploy, then indexed CONCURRENTLY in a later file.**

1. Declare the field in `app/utilities/storage/document_lookup_catalog.py`
   (or `platform_lookup_catalog.py`) and add the column with the helper of
   `1122_online_lookup_columns.sql`:

   ```sql
   select workshop.add_lookup_column('contacts', 'last_seen_at', 'bigint');
   ```

   It adds `doc_<field>` (`text` or `bigint`, nullable, no default: a
   catalog change, no rewrite) and recreates the table's
   `<table>_lookup_columns` trigger, which fills every such column of a row
   from its document on each insert and on each update of `document`
   (`workshop.fill_lookup_columns()`). The column is filled for every row
   written from then on, by either release.
2. After the deploy, fill the rows written before it:

   ```bash
   workshop backfill-lookup --collection contacts --field last_seen_at --batch 5000
   workshop backfill-lookup --dry-run   # only count what is left
   workshop backfill-lookup             # every trigger-filled column
   ```

   It walks the table in primary-key order, one short platform-wide
   transaction per batch with a lock timeout (`--lock-timeout`, 5 s) and
   retries, and touches only rows whose column is empty and whose document
   has the field: idempotent, resumable, safe while the application
   writes. Never run it in `preDeployCommand`. A field that old documents
   do not hold yet comes from their upcaster: run
   `workshop migrate-documents --collection X` first (it rewrites them in
   the current shape, and the trigger fills the column).
3. Build the index in a later file with the no-transaction header:

   ```sql
   -- workshop:no-transaction
   create index concurrently if not exists contacts_doc_last_seen_at_idx
       on workshop.contacts (business_id, doc_last_seen_at, created_at, row_sequence);
   ```

   A concurrent build blocks no writes; after the backfill it is built
   once, compact, instead of growing row by row with the backfill's
   updates.

1122, the first file in the pattern and the only file of its release,
builds the indexes of its new columns in the same no-transaction file,
right after the columns: the lists of that release page by them from the
start (`tests/storage/test_list_query_plans.py`). Its backfill then updates
those indexes as it goes, which costs some index bloat on those tables
(`REINDEX CONCURRENTLY` reclaims it) but never blocks a write. Until
then, a page sorted by such a column skips the rows whose column is still
empty and a count by it does not count them: a row written before the
deploy shows up there once the backfill reached it
(`docs/operations/deploys.md`).

Lookup columns are filled by triggers, so the stored document stays the
only source of truth; a value of the wrong type (text in a `bigint`
column) fails the write, like the casts of the generated columns before.

## Lookup fields: how queries stay indexed

Every table has FORCED row-level security. Postgres evaluates the RLS
policy before any condition that is not leakproof, and only leakproof
conditions can become index conditions. `document ->> 'field' = $1` calls
the JSON operator, which is not leakproof, so an expression index on it is
never used (EXPLAIN shows a sequential scan); GIN containment (`@>`) is not
leakproof either. Queries therefore filter plain columns:

- A field that repositories query by is declared in
  `app/utilities/storage/document_lookup_catalog.py` and gets a column
  `doc_<field>` with a btree index unless it is a FILTER_TEXT field that
  only narrows an indexed query. Up to 1114 these were stored generated
  columns (`1010_hot_path_lookup_indexes.sql`); from 1122 on they are
  trigger-filled (above). A plain `doc_<field>` column is trigger-filled by
  that rule: the trigger's arguments, `workshop backfill-lookup` and the
  tests read the columns from the catalog, with no registry to keep in
  step.
- A field of the objects in a list (`members[].user_id`) is kept in
  `workshop.document_lookup_keys` by the `workshop.sync_document_lookup_keys`
  trigger (one `create trigger` line per field, plus a backfill).
- The storage adapters refuse undeclared fields
  (`UndeclaredLookupFieldError`), in memory too, so a query without an
  index fails in unit tests. `tests/storage/test_lookup_fields_on_postgres.py`
  checks that every declared field has its column, index or trigger, and
  `tests/storage/test_hot_path_query_plans.py` that the hot queries use
  their index on realistic tables.
- Keyset pages (`page_by`), the newest document per group (`latest_by`)
  and grouped counts (`count_by`) sort, probe and group by these columns
  too: `1042_list_pages_and_aggregates.sql` and
  `1122_online_lookup_columns.sql` add the sort and group columns of the
  cabinet's lists and dashboards with indexes that start with
  `business_id` (platform-wide lists such as the admin client list without
  it), and `tests/storage/test_list_query_plans.py` checks each list,
  count and sum uses its index. A page with no sort field walks a table in
  first-write order on its `_order_idx` (the periodic jobs' walk over the
  businesses).
