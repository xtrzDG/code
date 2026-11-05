-- 1020_inbox_and_outbox
--
-- Never lose a customer message. Webhooks of Meta, Telegram, the platform
-- bot and ElevenLabs only verify the request and store it in
-- workshop.inbound_events ("insert ... on conflict do nothing": a
-- redelivered webhook finds its event), then the background worker
-- answers it. Replies and staff notifications go into
-- workshop.outbound_messages (one row per idempotency key) and the worker
-- sends them with retries until they are delivered or dead.
--
-- inbound_events is a platform collection (staff-bot updates and
-- finished-call reports have no business yet); outbound_messages belongs
-- to one business and gets the usual row-level security.
--
-- Event ids are derived from the business, channel and provider message
-- id, so the primary key already rejects a second copy; the unique index
-- below says the same in the schema (a platform event has no business:
-- coalesce makes its NULL compare equal).

select workshop.create_document_collection('inbound_events');
select workshop.create_document_collection('outbound_messages');

-- The inbox: one event per business, channel and provider message; purged
-- after 30 days.
alter table workshop.inbound_events
    add column if not exists doc_channel text
        generated always as (document ->> 'channel') stored,
    add column if not exists doc_provider_message_id text
        generated always as (document ->> 'provider_message_id') stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create unique index if not exists inbound_events_doc_message_idx
    on workshop.inbound_events
        (coalesce(business_id, ''), doc_channel, doc_provider_message_id);
create index if not exists inbound_events_doc_created_at_idx
    on workshop.inbound_events (doc_created_at);

-- The outbox: one message per business and idempotency key; the waiting
-- messages of one recipient (sent in order); purged after 30 days.
alter table workshop.outbound_messages
    add column if not exists doc_idempotency_key text
        generated always as (document ->> 'idempotency_key') stored,
    add column if not exists doc_recipient_key text
        generated always as (document ->> 'recipient_key') stored,
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create unique index if not exists outbound_messages_doc_idempotency_key_idx
    on workshop.outbound_messages (business_id, doc_idempotency_key);
create index if not exists outbound_messages_doc_recipient_key_idx
    on workshop.outbound_messages (business_id, doc_recipient_key);
create index if not exists outbound_messages_doc_created_at_idx
    on workshop.outbound_messages (doc_created_at);
