-- 1113_exports_and_suppression_list
--
-- Data-subject rights that reach every collection, a durable opt-out list
-- and the owner's exports.
--
-- suppression_entries (business collection): the customers who said STOP,
--   as an HMAC-SHA256 of their number or channel account under the
--   platform's suppression key. Read by id only (the id derives from the
--   business and the digest), so no lookup column. Kept through erasure.
--
-- business_exports (business collection): full exports of a business's
--   data (a ZIP in the export storage behind a signed 24-hour link).
--     (business_id, doc_created_at)  a business's exports, newest first
--     (doc_expires_at)               the hourly purge of expired archives,
--                                    across businesses
--
-- Erasure finds every trace of a customer by an index:
--     missed_calls    (business_id, doc_caller_phone_number)  their number
--     inbound_events  (business_id, doc_customer_channel_user_id)  their
--                     channel account (the customer message's sender; a
--                     row written before schema version 5 has it only
--                     inside `customer_message`, which the column reads)
--     inbound_events  (business_id, doc_conversation_id)  their
--                     conversations (finished-call reports among them)
--   outbound_messages (recipient_key) and feedback_requests (contact_id)
--   are indexed already (1020, 1062).
--
-- contacts (business_id, doc_created_at): the contacts CSV and the full
--   export page through a business's customers by when they first wrote.
--
-- Plain generated columns, as in 1010 and 1042 (forced row-level security
-- uses an index only for leakproof conditions on plain columns). The
-- missed calls and the inbox are purged after 90 and 30 days, so adding
-- their stored columns rewrites small tables once.

select workshop.create_document_collection('suppression_entries');
select workshop.create_document_collection('business_exports');

alter table workshop.business_exports
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored,
    add column if not exists doc_expires_at bigint
        generated always as ((document ->> 'expires_at')::bigint) stored;
create index if not exists business_exports_doc_created_at_idx
    on workshop.business_exports (business_id, doc_created_at);
create index if not exists business_exports_doc_expires_at_idx
    on workshop.business_exports (doc_expires_at);

alter table workshop.missed_calls
    add column if not exists doc_caller_phone_number text
        generated always as (document ->> 'caller_phone_number') stored;
create index if not exists missed_calls_doc_caller_phone_number_idx
    on workshop.missed_calls (business_id, doc_caller_phone_number);

alter table workshop.inbound_events
    add column if not exists doc_customer_channel_user_id text
        generated always as (
            coalesce(
                document ->> 'customer_channel_user_id',
                document -> 'customer_message' ->> 'channel_user_id'
            )
        ) stored,
    add column if not exists doc_conversation_id text
        generated always as (document ->> 'conversation_id') stored;
create index if not exists inbound_events_doc_customer_channel_user_id_idx
    on workshop.inbound_events (business_id, doc_customer_channel_user_id);
create index if not exists inbound_events_doc_conversation_id_idx
    on workshop.inbound_events (business_id, doc_conversation_id);

alter table workshop.contacts
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists contacts_doc_created_at_idx
    on workshop.contacts (business_id, doc_created_at);
