-- 1061_value_reports
--
-- What the assistant is worth to a business, shown in the cabinet and sent
-- to its owners.
--
-- value_settings: the average check of one business (what a booking or an
--   order brings), one document per business (id derived from it), read
--   by id. Kept apart from the business profile, which the assistant reads.
-- digest_preferences: which summaries one owner gets (daily, weekly,
--   monthly), one document per business and user (id derived from them),
--   read by id.
-- value_reports: the stored daily and weekly digests and monthly reports,
--   one per business, kind and period (id derived from them), so the
--   hourly job never sends a period twice. The cabinet's Reports page
--   pages them by kind, newest period first:
--     (business_id, doc_kind, doc_starts_at)
--
-- Plain generated columns, as in 1010 and 1042 (forced row-level security
-- uses an index only for leakproof conditions on plain columns). The
-- tables are new, so adding the columns rewrites nothing.

select workshop.create_document_collection('value_settings');
select workshop.create_document_collection('digest_preferences');
select workshop.create_document_collection('value_reports');

alter table workshop.value_reports
    add column if not exists doc_kind text
        generated always as (document ->> 'kind') stored,
    add column if not exists doc_starts_at bigint
        generated always as ((document ->> 'starts_at')::bigint) stored;
create index if not exists value_reports_doc_kind_starts_at_idx
    on workshop.value_reports (business_id, doc_kind, doc_starts_at);
create index if not exists value_reports_doc_starts_at_idx
    on workshop.value_reports (business_id, doc_starts_at);
