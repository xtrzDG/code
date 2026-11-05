# 0001. Tenant data as JSONB documents in Postgres behind a document-store contract

- Status: Accepted
- Date: 2026-10-02

## Context

The product stores many small aggregates per business: the business with
its team and settings, the assistant profile, knowledge items, versions,
conversations and messages, bookings, leads, invoices, audit entries. Their
shapes changed weekly while the questionnaire, niches and channels were
being built, and every record belongs to exactly one business, which must
never see another's data. The use cases had to be testable without a
database.

## Decision

- Each aggregate is a pydantic document (`app/schemas/domain/`) stored as a
  JSONB row in its own Postgres table (`app/adapters/storage/postgres/`),
  with `id`, `business_id` and timestamps as columns. The catalog of
  collections is `app/utilities/storage/document_collection_catalog.py`;
  SQL migrations live in `migrations/` and run with
  `python -m app.gateways.cli.migrate`.
- Use cases see only `DocumentCollectionContract` (`app/contracts/document_store.py`)
  through repositories; tests use `InMemoryDocumentCollectionAdapter`
  with the same behaviour.
- Isolation is enforced twice: repositories read tenant documents only
  together with their `business_id` (`BusinessScopedRepository`), and
  Postgres row-level security binds every request and job to its business
  (`StorageScopeContract.scoped_to_business`).

## Consequences

- Fast iteration: a new field is a model change, not a migration. In
  exchange, documents need explicit evolution rules (tolerant reads,
  upcasters) once old rows must survive rolling deploys.
- Queries beyond "by id" and "by business" need indexes on extracted
  fields or generated columns; a scan over JSONB grows with the data, so
  hot lookups are indexed explicitly.
- RLS is the safety net, not the only guard: a repository that forgets the
  business filter still cannot read foreign rows.
