"""SQL of the periodic job runs on `workshop.periodic_job_runs` (migration 1011)."""

from typing import LiteralString

from psycopg import sql

from app.adapters.storage.postgres.postgres_session_settings import (
    DOCUMENT_SCHEMA_NAME,
)

PERIODIC_JOB_RUNS_COLLECTION: str = "periodic_job_runs"
PERIODIC_JOB_RUNS_TABLE: sql.Identifier = sql.Identifier(
    DOCUMENT_SCHEMA_NAME,
    PERIODIC_JOB_RUNS_COLLECTION,
)
# Only one worker decides about one job at a time; the others do not wait
# (false: someone else is starting it right now). The lock ends with the
# transaction, the run record keeps the job's lease after that.
TRY_JOB_LOCK: LiteralString = (
    "select pg_try_advisory_xact_lock("
    "hashtextextended('periodic_job_runs:' || %s::text, 0))"
)
SELECT_RUN: sql.Composed = sql.SQL(
    "select document::text from {table} where document_key = %s for update"
).format(table=PERIODIC_JOB_RUNS_TABLE)
UPSERT_RUN: sql.Composed = sql.SQL(
    "insert into {table} "
    "(document_key, business_id, document, created_at, updated_at) "
    "values (%s, null, %s::jsonb, %s, %s) "
    "on conflict (document_key) do update set "
    "document = excluded.document, updated_at = excluded.updated_at"
).format(table=PERIODIC_JOB_RUNS_TABLE)
DELETE_STARTED_BEFORE: sql.Composed = sql.SQL(
    "delete from {table} where created_at < %s"
).format(table=PERIODIC_JOB_RUNS_TABLE)
