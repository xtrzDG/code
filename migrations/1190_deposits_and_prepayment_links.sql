-- 1190_deposits_and_prepayment_links
--
-- Deposits and prepayment links (W19-DEPOSITS): a booking or a banquet
-- request a deposit policy covers gets the owner's own payment link, its
-- place is held until the deposit is paid or the hold runs out, and the
-- reports compare the no-shows of bookings with and without one.
-- Online-safe (migrations/README.md): one transaction; the two tables are
-- new and empty, so their lookup columns (trigger-filled, as every lookup
-- column from 1122 on) and indexes are built right here; on bookings, an
-- existing table, it only adds a trigger-filled column and builds no index.
--
-- deposit_settings (business collection): one document per business, by id.
-- deposit_requests (business collection): one deposit asked.
--   (business_id, doc_booking_id)            the deposit of a booking
--   (business_id, doc_lead_id)               the deposit of a banquet request
--   (doc_status, doc_hold_expires_at)        across businesses: holds that
--                                            ran out (the minute's sweep)
--   (doc_status, doc_reminder_due_at)        across businesses: reminders due
--   (doc_settle_after)                       across businesses: cancelled
--                                            paid bookings to settle
--   (business_id, doc_status, doc_paid_at)   the reports' collected sums,
--     include (doc_currency_code,            summed per currency from the
--              doc_amount_minor,             index alone (as 1083 does for
--              doc_is_sandbox)               booking values)
--   (business_id, doc_requested_at)          the reports' requests of a period
--
-- bookings (version 6): (doc_deposit_status), a trigger-filled FILTER_TEXT
--   column that narrows the reports' grouped counts of a period (the
--   start-time index reads the period). Rows written before this file never
--   had a deposit, so a missing value in them is right: nothing to backfill.

select workshop.create_document_collection('deposit_settings');
select workshop.create_document_collection('deposit_requests');

select workshop.add_lookup_column('deposit_requests', 'booking_id', 'text');
select workshop.add_lookup_column('deposit_requests', 'lead_id', 'text');
select workshop.add_lookup_column('deposit_requests', 'status', 'text');
select workshop.add_lookup_column('deposit_requests', 'hold_expires_at', 'bigint');
select workshop.add_lookup_column('deposit_requests', 'reminder_due_at', 'bigint');
select workshop.add_lookup_column('deposit_requests', 'settle_after', 'bigint');
select workshop.add_lookup_column('deposit_requests', 'paid_at', 'bigint');
select workshop.add_lookup_column('deposit_requests', 'requested_at', 'bigint');
select workshop.add_lookup_column('deposit_requests', 'amount_minor', 'bigint');
select workshop.add_lookup_column('deposit_requests', 'currency_code', 'text');
select workshop.add_lookup_column('deposit_requests', 'is_sandbox', 'text');
create index if not exists deposit_requests_doc_booking_id_idx
    on workshop.deposit_requests (business_id, doc_booking_id);
create index if not exists deposit_requests_doc_lead_id_idx
    on workshop.deposit_requests (business_id, doc_lead_id);
create index if not exists deposit_requests_doc_hold_expires_at_idx
    on workshop.deposit_requests (doc_status, doc_hold_expires_at);
create index if not exists deposit_requests_doc_reminder_due_at_idx
    on workshop.deposit_requests (doc_status, doc_reminder_due_at);
create index if not exists deposit_requests_doc_settle_after_idx
    on workshop.deposit_requests (doc_settle_after);
create index if not exists deposit_requests_doc_paid_at_idx
    on workshop.deposit_requests (business_id, doc_status, doc_paid_at)
    include (doc_currency_code, doc_amount_minor, doc_is_sandbox);
create index if not exists deposit_requests_doc_requested_at_idx
    on workshop.deposit_requests (business_id, doc_requested_at, row_sequence);

select workshop.add_lookup_column('bookings', 'deposit_status', 'text');
