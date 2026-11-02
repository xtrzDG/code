-- 1230_platform_brakes_and_watchers
--
-- The platform's safety switches and watchers (A9): a global pause of
-- every assistant, heartbeats of the periodic jobs that the missed-run
-- alert reads without Sentry, and the daily payment reconciliation with
-- Flitt and Stripe. All three are platform collections: their rows name
-- no business, so the tenant role holds no privilege on them (1200).
--
-- platform_pauses (platform collection): one row, stored under
--   `platform`; read by its key on every model turn and call.
-- periodic_job_heartbeats (platform collection): one row per periodic job,
--   stored under the job's name;
--   (doc_due_by)   the platform alerts job's overdue heartbeats
--                  (`due_by` before now), every five minutes
-- payment_reconciliations (platform collection): one row per UTC day,
--   read by its key (today's, else yesterday's).
--
-- Online-safe (migrations/README.md): one transaction; the tables are new
-- and empty, so their lookup column and index are built right here. No
-- existing table changes; the new `platform_alert_states` codes are
-- stored and read under their code (version 8 of the alert state).

select workshop.create_platform_collection('platform_pauses');

select workshop.create_platform_collection('periodic_job_heartbeats');
select workshop.add_lookup_column('periodic_job_heartbeats', 'due_by', 'bigint');
create index if not exists periodic_job_heartbeats_doc_due_by_idx
    on workshop.periodic_job_heartbeats (doc_due_by);

select workshop.create_platform_collection('payment_reconciliations');
