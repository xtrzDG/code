-- 1011_leased_job_queue
--
-- Several background workers share one job queue, and periodic jobs run
-- once per period across workers and restarts.
--
-- Queued jobs (workshop.queued_jobs, see 0001) carry a lane ("inbound",
-- "outbound", "default", "autotests"), an optional serial key, and while a
-- worker runs one: status "running", lease_until (UNIX microseconds) and a
-- lease token. Workers claim due jobs of a lane with
--
--   update ... where document_key in (select ... for update skip locked)
--
-- (app/adapters/storage/postgres/job_claim_queries.py), extend the lease
-- while a job runs, and release jobs whose lease ended (their worker died).
-- Finished jobs (done, dead, discarded) are purged after 30 days.
--
-- Periodic job runs: one row per job and period (document_key
-- "<job name>:<period key>"), written under pg_try_advisory_xact_lock of the
-- job name, so a daily job runs once per day even when two workers tick at
-- the same moment or the worker restarts.

select workshop.create_document_collection('periodic_job_runs');

-- Claims: due pending jobs of one lane, oldest first.
create index if not exists queued_jobs_claim_idx
    on workshop.queued_jobs (
        (document ->> 'lane'),
        ((document ->> 'run_at')::bigint),
        row_sequence
    )
    where document ->> 'status' = 'pending';

-- The reaper: running jobs by the end of their lease.
create index if not exists queued_jobs_lease_idx
    on workshop.queued_jobs (((document ->> 'lease_until')::bigint))
    where document ->> 'status' = 'running';

-- One job per serial key at a time: running jobs by serial key.
create index if not exists queued_jobs_running_serial_key_idx
    on workshop.queued_jobs ((document ->> 'serial_key'))
    where document ->> 'status' = 'running';

-- The admin list (newest change first, optionally by status) and the purge
-- of finished jobs.
create index if not exists queued_jobs_status_updated_idx
    on workshop.queued_jobs (
        (document ->> 'status'),
        ((document ->> 'updated_at')::bigint),
        document_key
    );
create index if not exists queued_jobs_updated_idx
    on workshop.queued_jobs (((document ->> 'updated_at')::bigint), document_key);

-- Replaced by queued_jobs_claim_idx: due jobs are claimed per lane.
drop index if exists workshop.queued_jobs_due_idx;
