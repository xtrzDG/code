-- 1163_service_level_indicators
--
-- workshop:no-transaction
--
-- The computed service level indicators (W15-METRICS-TRACING,
-- docs/operations/slo.md): what the error budget card of /admin/system
-- and the burn-rate alerts read. Online-safe (migrations/README.md):
-- statement by statement outside a transaction, every statement
-- idempotent, so the index on messages, an existing busy table, is built
-- CONCURRENTLY; the two collections are new and empty.
--
-- service_level_slots (platform collection): five minutes of one series
--   (customer messages answered within 60 s, API requests answered
--   without a server error), stored under `<series>:<slot_start>`.
--   (doc_series, doc_slot_start)   a series' slots of a window: the
--                                  burn rates over 5 min to 6 h, the purge
--                                  of slots older than 35 days
-- service_level_hours (platform collection): one row per hour with every
--   SLI of that hour, stored under its start.
--   (doc_hour_start)               the last 28 days (the error budget),
--                                  the newest row (where the job resumes)
-- messages: the assistant replies of an hour across every business,
--   bucketed by `reply_latency_ms` (the hour's answer p95): the existing
--   indexes lead with business_id, so this one leads with the author and
--   the creation time and carries the latency (an index-only scan).

select workshop.create_document_collection('service_level_slots');
select workshop.create_document_collection('service_level_hours');

select workshop.add_lookup_column('service_level_slots', 'series', 'text');
select workshop.add_lookup_column('service_level_slots', 'slot_start', 'bigint');
create index concurrently if not exists service_level_slots_doc_series_idx
    on workshop.service_level_slots (doc_series, doc_slot_start);

select workshop.add_lookup_column('service_level_hours', 'hour_start', 'bigint');
create index concurrently if not exists service_level_hours_doc_hour_start_idx
    on workshop.service_level_hours (doc_hour_start);

create index concurrently if not exists messages_doc_platform_reply_latency_idx
    on workshop.messages (doc_author, doc_created_at)
    include (doc_reply_latency_ms);
