-- 1111_status_page_and_help
--
-- The public status page, the cabinet's announcement banner and the
-- guidance each person has seen (docs/operations/status-page.md).
--
-- Three platform collections (no business owns their rows):
--
--   platform_announcements  what the platform team tells every owner (an
--                           outage, slow answers, planned maintenance):
--                           the ones in effect by doc_status, those
--                           resolved in the last ninety days by
--                           doc_resolved_at, the admin's pages newest
--                           first by doc_created_at
--   platform_status_days    one row per UTC day of the status history,
--                           stored under the day (read by key)
--   help_progress           one row per person, stored under the user's
--                           id: the coach marks they closed and the newest
--                           "What's new" entry they read (read by key)
--
-- The tables are new and empty, so their generated columns and indexes
-- cost nothing to add.

select workshop.create_document_collection('platform_announcements');
select workshop.create_document_collection('platform_status_days');
select workshop.create_document_collection('help_progress');

alter table workshop.platform_announcements
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored,
    add column if not exists doc_resolved_at bigint
        generated always as ((document ->> 'resolved_at')::bigint) stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists platform_announcements_doc_status_idx
    on workshop.platform_announcements (doc_status);
create index if not exists platform_announcements_doc_resolved_at_idx
    on workshop.platform_announcements (doc_resolved_at);
create index if not exists platform_announcements_doc_created_at_idx
    on workshop.platform_announcements (doc_created_at, created_at, row_sequence);
