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
