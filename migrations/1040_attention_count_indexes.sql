-- 1040_attention_count_indexes
--
-- The badges of the cabinet's navigation (GET .../attention-counts): open
-- handoffs, new requests, upcoming bookings to confirm and channels in
-- error of one business. The cabinet asks again after every live event, so
-- each count is one index lookup of the business and a status, never a
-- read of its documents. `is_sandbox` (the owner's test chat, autotests)
-- only narrows those rows, so it gets a column without an index. The lookup
-- fields are declared in app/utilities/storage/document_lookup_fields.py.
--
-- Adding stored columns rewrites the tables under an exclusive lock; at
-- today's table sizes that takes seconds.

alter table workshop.handoffs
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored,
    add column if not exists doc_is_sandbox text
        generated always as (document ->> 'is_sandbox') stored;
create index if not exists handoffs_doc_status_idx
    on workshop.handoffs (business_id, doc_status);

alter table workshop.leads
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored,
    add column if not exists doc_is_sandbox text
        generated always as (document ->> 'is_sandbox') stored;
create index if not exists leads_doc_status_idx
    on workshop.leads (business_id, doc_status);

-- Bookings to confirm are the pending ones that have not started yet; the
-- start time (UNIX seconds) follows the status in the index.
alter table workshop.bookings
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored,
    add column if not exists doc_is_sandbox text
        generated always as (document ->> 'is_sandbox') stored,
    add column if not exists doc_starts_at bigint
        generated always as ((document ->> 'starts_at')::bigint) stored;
create index if not exists bookings_doc_status_starts_at_idx
    on workshop.bookings (business_id, doc_status, doc_starts_at);

alter table workshop.channels
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored;
create index if not exists channels_doc_status_idx
    on workshop.channels (business_id, doc_status);
