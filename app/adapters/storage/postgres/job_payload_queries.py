"""
SQL that finds the waiting or running jobs of given payloads (see
migration 1011): the sweeper of the inbox asks which stale events still
have a job before it queues one again. Few jobs wait or run at any time,
so the status index of 1011 narrows the read; values are bind parameters.
"""

from psycopg import sql

from app.adapters.storage.postgres.job_claim_queries import QUEUED_JOBS_TABLE

ACTIVE_JOB_STATUSES: tuple[str, ...] = ("pending", "running")

ACTIVE_PAYLOADS: sql.Composed = sql.SQL(
    """
    select distinct document ->> 'payload'
    from {table}
    where document ->> 'status' = any(%(statuses)s::text[])
      and document ->> 'name' = %(name)s
      and document ->> 'payload' = any(%(payloads)s::text[])
    """
).format(table=QUEUED_JOBS_TABLE)
