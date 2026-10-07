-- 1094_inbound_event_sweep
--
-- The sweeper of the inbox (`sweep_stale_inbound_events`, every few
-- minutes, platform-wide) looks for events that should have been processed
-- long ago: still RECEIVED or PROCESSING twice the processing lease after
-- they arrived, or FAILED and an hour old. It reads them by status and by
-- the moment they arrived, oldest first, so both are columns of one index
-- (a platform table: the index does not start with the business).
--
-- The status is a generated column like the other lookup fields
-- (migrations/README.md): RLS keeps JSON expressions out of index
-- conditions. The inbox is purged after 30 days, so the table is small.

alter table workshop.inbound_events
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored;
create index if not exists inbound_events_doc_status_created_at_idx
    on workshop.inbound_events (doc_status, doc_created_at);
