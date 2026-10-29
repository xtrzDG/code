-- 1181_public_api_and_webhooks
--
-- The public API and outbound webhooks (R15-PUBLIC-API-WEBHOOKS):
-- Settings → Integrations, `/v1/public-api/*` and the Zapier app.
-- Online-safe (migrations/README.md): one transaction; the three tables are
-- new and empty, so their lookup columns (trigger-filled, as every lookup
-- column from 1122 on) and indexes are built right here.
--
-- webhook_endpoints (business collection): the addresses a business has
--   its events sent to.
--   (business_id, doc_status)               the active endpoints an event
--                                           goes to (every announced change)
--   (business_id, doc_created_at)           the cabinet's list, oldest first
-- webhook_deliveries (business collection): one event's delivery to one
--   endpoint with its attempts.
--   (business_id, doc_endpoint_id, doc_created_at)  an endpoint's delivery
--                                           log, newest first
--   (business_id, doc_contact_id)           a customer's deliveries (the
--                                           erasure of their data)
--   (doc_expires_at)                        across businesses: the daily
--                                           purge of deliveries past 30 days
-- api_keys (business collection): the keys of the public API.
--   (doc_secret_hash) unique                across businesses: the key of a
--                                           request, by its SHA-256
--   (business_id, doc_created_at)           the cabinet's list

select workshop.create_document_collection('webhook_endpoints');
select workshop.create_document_collection('webhook_deliveries');
select workshop.create_document_collection('api_keys');

select workshop.add_lookup_column('webhook_endpoints', 'status', 'text');
select workshop.add_lookup_column('webhook_endpoints', 'created_at', 'bigint');
create index if not exists webhook_endpoints_doc_status_idx
    on workshop.webhook_endpoints (business_id, doc_status);
create index if not exists webhook_endpoints_doc_created_at_idx
    on workshop.webhook_endpoints (business_id, doc_created_at, row_sequence);

select workshop.add_lookup_column('webhook_deliveries', 'endpoint_id', 'text');
select workshop.add_lookup_column('webhook_deliveries', 'created_at', 'bigint');
select workshop.add_lookup_column('webhook_deliveries', 'expires_at', 'bigint');
select workshop.add_lookup_column('webhook_deliveries', 'contact_id', 'text');
create index if not exists webhook_deliveries_doc_endpoint_id_idx
    on workshop.webhook_deliveries
    (business_id, doc_endpoint_id, doc_created_at, row_sequence);
create index if not exists webhook_deliveries_doc_contact_id_idx
    on workshop.webhook_deliveries (business_id, doc_contact_id);
create index if not exists webhook_deliveries_doc_expires_at_idx
    on workshop.webhook_deliveries (doc_expires_at);

select workshop.add_lookup_column('api_keys', 'secret_hash', 'text');
select workshop.add_lookup_column('api_keys', 'created_at', 'bigint');
create unique index if not exists api_keys_doc_secret_hash_idx
    on workshop.api_keys (doc_secret_hash);
create index if not exists api_keys_doc_created_at_idx
    on workshop.api_keys (business_id, doc_created_at, row_sequence);
