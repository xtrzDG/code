-- 1173_platform_monitors
--
-- A watchdog that does not run on the workers (W17-PIPELINE-WATCHDOG):
-- the API's pipeline watchdog and an honest status page
-- (docs/operations/runbooks/worker-down.md, status-page-stale.md).
--
-- platform_monitors (platform collection): one row per watcher of the
--   platform, stored under its name (`alert_checks`: the workers'
--   platform_alerts job; `pipeline_watchdog`: the API's watchdog): when
--   it last finished a look, and for the watchdog which API process
--   leads it until when. Every read is by those names (`get`), so the
--   table needs no lookup column; it holds two rows.
--
-- The table is new and empty: online-safe as it is. The other changes of
-- this release are in documents only (expand and contract): the
-- `worker_down` alert state is stored and read under its code, and the
-- incidents' new fields are optional.

select workshop.create_document_collection('platform_monitors');
