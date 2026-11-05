-- 1143_admin_actions_and_client_story
--
-- The admin acts on a client's account and keeps the client's story
-- (R13-ADMIN-ACTIONS).
--
-- billing_credits (business collection): the credit ledger. A platform
--   admin's grant (with who and why) and the credit an invoice used when
--   it was issued. The balance reads a business's lines through the
--   business index the table already has: no lookup column.
--
-- client_notes (business collection): the platform team's notes about a
--   client, pinned first; read per business through the same index.
--
-- client_health_changes (business collection): a client's health moved
--   from one status to another, written by refresh_client_standings.
--     (changed_at)          the client's timeline, newest first
--     (status, changed_at)  the daily digest of clients that newly turned
--                           critical, across businesses
--
-- admin_digest_states (platform collection): how far each digest of the
--   platform team has looked; read by its kind.
--
-- subscriptions (version 3: a discount and a waived setup fee), invoices
-- (version 3: discount, credit and a payment recorded by hand) and
-- audit_log_entries (version 5: the ADMIN_* actions and their reason) gain
-- optional fields nobody queries by: no column, no index.
--
-- The tables are new and empty, so their lookup columns (trigger-filled,
-- as every lookup column from 1122 on) and indexes are added right here.

select workshop.create_document_collection('billing_credits');
select workshop.create_document_collection('client_notes');
select workshop.create_document_collection('client_health_changes');
select workshop.create_document_collection('admin_digest_states');

select workshop.add_lookup_column('client_health_changes', 'changed_at', 'bigint');
select workshop.add_lookup_column('client_health_changes', 'status', 'text');
create index if not exists client_health_changes_doc_changed_at_idx
    on workshop.client_health_changes (business_id, doc_changed_at, row_sequence);
create index if not exists client_health_changes_doc_status_idx
    on workshop.client_health_changes (doc_status, doc_changed_at);
