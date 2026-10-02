"""
SQL of the leased job queue on `workshop.queued_jobs` (see migration 1011).

Every statement runs platform-wide (queued jobs are a platform collection)
and takes its times from the caller's clock, like the in-memory twin. Job
fields are read with `document ->> 'field'` so the partial indexes of 1011
match; values are always bind parameters.
"""

from typing import LiteralString

from psycopg import sql

from app.adapters.storage.postgres.postgres_session_settings import (
    DOCUMENT_SCHEMA_NAME,
)

QUEUED_JOBS_COLLECTION: str = "queued_jobs"
QUEUED_JOBS_TABLE: sql.Identifier = sql.Identifier(
    DOCUMENT_SCHEMA_NAME,
    QUEUED_JOBS_COLLECTION,
)
# Claims of one lane are serialized with this transaction-level lock (taken
# in its own statement, so the claim's snapshot sees the previous claim).
# Then "at most one running job per serial key" holds across workers.
LANE_CLAIM_LOCK: LiteralString = (
    "select pg_advisory_xact_lock("
    "hashtextextended('queued_jobs_claim:' || %s::text, 0))"
)
FINISHED_JOB_STATUSES: tuple[str, ...] = ("done", "dead", "discarded")
PURGE_BATCH_SIZE: int = 1000

# Due pending jobs of the lane, oldest first, the oldest one per serial key
# (and none whose key already runs); locked rows are skipped, not waited
# for. The claimed jobs turn RUNNING with one more attempt and the lease.
CLAIM_DUE: sql.Composed = sql.SQL(
    """
    with heads as (
        select distinct on (
            coalesce(pending.document ->> 'serial_key', pending.document_key)
        )
            pending.document_key,
            (pending.document ->> 'run_at')::bigint as run_at,
            pending.row_sequence
        from {table} as pending
        where pending.document ->> 'status' = 'pending'
          and pending.document ->> 'lane' = %(lane)s
          and (pending.document ->> 'run_at')::bigint <= %(now)s
          and not exists (
              select 1
              from {table} as running
              where running.document ->> 'status' = 'running'
                and running.document ->> 'serial_key'
                    = pending.document ->> 'serial_key'
          )
        order by
            coalesce(pending.document ->> 'serial_key', pending.document_key),
            (pending.document ->> 'run_at')::bigint,
            pending.row_sequence
    ),
    picked as (
        select jobs.document_key
        from {table} as jobs
        join heads on heads.document_key = jobs.document_key
        where jobs.document ->> 'status' = 'pending'
        order by heads.run_at, heads.row_sequence
        limit %(limit)s
        for update of jobs skip locked
    )
    update {table} as jobs
    set document = jobs.document || jsonb_build_object(
            'status', 'running',
            'attempts', (jobs.document ->> 'attempts')::integer + 1,
            'lease_until', %(lease_until)s::bigint,
            'lease_token', %(lease_token)s::text,
            'updated_at', %(now)s::bigint
        ),
        updated_at = %(now)s
    from picked
    where jobs.document_key = picked.document_key
    returning jobs.document::text
    """
).format(table=QUEUED_JOBS_TABLE)

# Heartbeat: only leases still held under their claim's token move.
EXTEND_LEASES: sql.Composed = sql.SQL(
    """
    update {table} as jobs
    set document = jsonb_set(
        jobs.document, '{{lease_until}}', to_jsonb(%(lease_until)s::bigint)
    )
    from unnest(%(job_ids)s::text[], %(lease_tokens)s::text[])
        as held(document_key, lease_token)
    where jobs.document_key = held.document_key
      and jobs.document ->> 'status' = 'running'
      and jobs.document ->> 'lease_token' = held.lease_token
    returning jobs.document_key
    """
).format(table=QUEUED_JOBS_TABLE)

# Reaper: running jobs whose lease ended go back to pending (due now), or
# die after their last attempt.
RELEASE_EXPIRED_LEASES: sql.Composed = sql.SQL(
    """
    update {table} as jobs
    set document = jobs.document || jsonb_build_object(
            'status',
            case
                when (jobs.document ->> 'attempts')::integer >= %(max_attempts)s
                then 'dead'
                else 'pending'
            end,
            'run_at', %(now)s::bigint,
            'lease_until', null,
            'lease_token', null,
            'last_error', %(error_text)s::text,
            'updated_at', %(now)s::bigint
        ),
        updated_at = %(now)s
    where jobs.document ->> 'status' = 'running'
      and (jobs.document ->> 'lease_until')::bigint < %(now)s
    returning jobs.document::text
    """
).format(table=QUEUED_JOBS_TABLE)

# Finished jobs, a batch at a time, so a long backlog never holds many
# row locks in one transaction.
PURGE_FINISHED_BATCH: sql.Composed = sql.SQL(
    """
    delete from {table}
    where document_key in (
        select document_key
        from {table}
        where document ->> 'status' = any(%(statuses)s::text[])
          and (document ->> 'updated_at')::bigint < %(finished_before)s
        limit %(batch_size)s
    )
    """
).format(table=QUEUED_JOBS_TABLE)


def build_list_page_query(
    has_status: bool,
    has_name: bool,
    has_position: bool,
) -> sql.Composed:
    """
    Jobs, the most recently changed first (ties by key), filtered only by
    the given conditions, so each variant uses its index.
    """

    conditions: list[sql.Composable] = []
    if has_status:
        conditions.append(sql.SQL("document ->> 'status' = %(status)s"))

    if has_name:
        conditions.append(sql.SQL("document ->> 'name' = %(name)s"))

    if has_position:
        conditions.append(
            sql.SQL(
                "((document ->> 'updated_at')::bigint, document_key) "
                "< (%(after_updated_at)s, %(after_key)s)"
            )
        )

    where: sql.Composable = (
        sql.SQL("where ") + sql.SQL(" and ").join(conditions)
        if conditions
        else sql.SQL("")
    )
    return sql.SQL(
        "select document::text from {table} {where} "
        "order by (document ->> 'updated_at')::bigint desc, document_key desc "
        "limit %(limit)s"
    ).format(table=QUEUED_JOBS_TABLE, where=where)
