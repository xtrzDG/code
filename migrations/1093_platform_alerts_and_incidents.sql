-- 1093_platform_alerts_and_incidents
--
-- The platform's own operations: alerts the team gets before owners
-- notice, the admin system page, and the incident log
-- (docs/operations/slo.md, docs/operations/incident.md).
--
-- Three platform collections (no business owns their rows):
--
--   platform_alert_states  the latest episode of each platform alert,
--                          stored under the alert's code (read by key)
--   maintenance_runs       each off-site backup and restore drill as it
--                          ended, the last of a kind found by
--                          (doc_kind, doc_finished_at)
--   incidents              the incident log, newest first by
--                          doc_created_at; a breach's affected businesses
--                          and owner notices are in the document
--
-- The system page and the alerts count across every business, so the
-- columns they filter get indexes that do not start with business_id
-- (platform-wide queries have no business to lead with):
--
--   queued_jobs   doc_status, doc_lane, doc_name and doc_run_at as plain
--                 generated columns: jobs counted by state and lane (only
--                 waiting, running and dead ones: done jobs are skipped by
--                 the index), the oldest due job of a lane. Forced
--                 row-level security uses an index only for leakproof
--                 conditions on plain columns (the expression indexes of
--                 1011 are not used under it).
--   handoffs      (doc_created_at): the handoffs of the last hour and of
--                 the last week, for the spike alert.
--   channels      (doc_status): the channels in ERROR; and the optional
--                 `credential_expires_at` of Meta channels (version 3 of
--                 the channel document) with its index: tokens that run
--                 out soon.
--
-- The outbox's (doc_created_at) index (1020) already serves the delivery
-- failure rate, and the lookup keys of `tool_calls[].is_error` (1042) the
-- tool errors. Adding stored generated columns rewrites queued_jobs and
-- channels once (both small: finished jobs are purged after 30 days).

select workshop.create_document_collection('platform_alert_states');
select workshop.create_document_collection('maintenance_runs');
select workshop.create_document_collection('incidents');

alter table workshop.maintenance_runs
    add column if not exists doc_kind text
        generated always as (document ->> 'kind') stored,
    add column if not exists doc_finished_at bigint
        generated always as ((document ->> 'finished_at')::bigint) stored;
create index if not exists maintenance_runs_doc_kind_finished_at_idx
    on workshop.maintenance_runs (doc_kind, doc_finished_at);

alter table workshop.incidents
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists incidents_doc_created_at_idx
    on workshop.incidents (doc_created_at, created_at, row_sequence);

alter table workshop.queued_jobs
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored,
    add column if not exists doc_lane text
        generated always as (document ->> 'lane') stored,
    add column if not exists doc_name text
        generated always as (document ->> 'name') stored,
    add column if not exists doc_run_at bigint
        generated always as ((document ->> 'run_at')::bigint) stored;
create index if not exists queued_jobs_doc_status_lane_run_at_idx
    on workshop.queued_jobs (doc_status, doc_lane, doc_run_at)
    include (doc_name);

create index if not exists handoffs_doc_created_at_platform_idx
    on workshop.handoffs (doc_created_at)
    include (doc_is_sandbox);

alter table workshop.channels
    add column if not exists doc_credential_expires_at bigint
        generated always as ((document ->> 'credential_expires_at')::bigint) stored;
create index if not exists channels_doc_status_platform_idx
    on workshop.channels (doc_status);
create index if not exists channels_doc_credential_expires_at_idx
    on workshop.channels (doc_credential_expires_at)
    where doc_credential_expires_at is not null;
