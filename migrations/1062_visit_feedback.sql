-- 1062_visit_feedback
--
-- Feedback after visits: a customer is asked how their visit went (1 to
-- 5) in their messenger and language, everyone who answers is invited to
-- the business's Google review page, and a low rating opens a handoff.
--
-- review_settings: the feedback settings of one business (on or off, the
--   delay after a visit, the WhatsApp template), id derived from the
--   business. The periodic job finds the businesses that ask across all
--   businesses: (doc_is_feedback_enabled).
-- feedback_requests: the request after one visit (a booking), id derived
--   from the business and the booking, so a visit is asked about once.
--   Read by id (the job, the outbox), by customer and status (a rating
--   answers the customer's waiting request), by public token (the review
--   link a customer opens, before the business is known), newest first by
--   business (Settings → Reviews), and counted per status with the sums of
--   the ratings and link visits of a period (the statistics; the index
--   carries those columns, so the counts read the index only).
--
-- Both belong to one business and get the usual row-level security. Plain
-- generated columns, as in 1010 and 1042 (forced row-level security uses
-- an index only for leakproof conditions on plain columns).

select workshop.create_document_collection('review_settings');
select workshop.create_document_collection('feedback_requests');

alter table workshop.review_settings
    add column if not exists doc_is_feedback_enabled text
        generated always as (document ->> 'is_feedback_enabled') stored;
create index if not exists review_settings_doc_is_feedback_enabled_idx
    on workshop.review_settings (doc_is_feedback_enabled);

alter table workshop.feedback_requests
    add column if not exists doc_contact_id text
        generated always as (document ->> 'contact_id') stored,
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored,
    add column if not exists doc_review_token text
        generated always as (document ->> 'review_token') stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored,
    add column if not exists doc_score bigint
        generated always as ((document ->> 'score')::bigint) stored,
    add column if not exists doc_review_clicks bigint
        generated always as ((document ->> 'review_clicks')::bigint) stored;
create index if not exists feedback_requests_doc_contact_status_idx
    on workshop.feedback_requests (business_id, doc_contact_id, doc_status);
create unique index if not exists feedback_requests_doc_review_token_idx
    on workshop.feedback_requests (doc_review_token);
create index if not exists feedback_requests_doc_created_at_idx
    on workshop.feedback_requests (business_id, doc_created_at)
    include (doc_status, doc_score, doc_review_clicks);
