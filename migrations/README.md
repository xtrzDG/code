# Database migrations

SQL migrations of the Postgres document storage (EU region). Applied in
version order by

```bash
DATABASE_URL=postgresql://... uv run python -m app.adapters.storage.postgres.migrate
DATABASE_URL=postgresql://... uv run python -m app.adapters.storage.postgres.migrate --dry-run
```

The runner records every applied file in `workshop.schema_migrations` with a
SHA-256 checksum, runs each pending file and its record in one transaction,
and serializes concurrent runners with an advisory lock, so it is safe on
every deploy.

Rules:

- Name files `NNNN_snake_case_slug.sql` with the next free 4-digit version.
- Never edit an applied file: the runner refuses a changed checksum. Add a
  new migration instead.
- No transaction control (`BEGIN`, `COMMIT`) and no statements that cannot
  run inside a transaction (`CREATE INDEX CONCURRENTLY`).
- A new document collection is one line:
  `select workshop.create_document_collection('collection_name');` — it
  creates the table, its indexes and the row-level security policy (see
  `0001_document_collections.sql` for the design). Add the name to
  `app/utilities/storage/document_collection_catalog.py` as well.

## Lookup fields: how queries stay indexed

Every table has FORCED row-level security. Postgres evaluates the RLS
policy before any condition that is not leakproof, and only leakproof
conditions can become index conditions. `document ->> 'field' = $1` calls
the JSON operator, which is not leakproof, so an expression index on it is
never used (EXPLAIN shows a sequential scan); GIN containment (`@>`) is not
leakproof either. Queries therefore filter plain columns:

- A field that repositories query by is declared in
  `app/utilities/storage/document_lookup_fields.py` and gets a stored
  generated column `doc_<field>` in a migration (see
  `1010_hot_path_lookup_indexes.sql`), with a btree index unless it is a
  FILTER_TEXT field that only narrows an indexed query:

  ```sql
  alter table workshop.bookings
      add column if not exists doc_starts_at bigint
          generated always as ((document ->> 'starts_at')::bigint) stored;
  create index if not exists bookings_doc_starts_at_idx
      on workshop.bookings (business_id, doc_starts_at);
  ```

- A field of the objects in a list (`members[].user_id`) is kept in
  `workshop.document_lookup_keys` by the `workshop.sync_document_lookup_keys`
  trigger (one `create trigger` line per field, plus a backfill).
- The storage adapters refuse undeclared fields
  (`UndeclaredLookupFieldError`), in memory too, so a query without an
  index fails in unit tests. `tests/storage/test_lookup_fields_on_postgres.py`
  checks that every declared field has its column, index or trigger, and
  `tests/storage/test_hot_path_query_plans.py` that the hot queries use
  their index on realistic tables.
