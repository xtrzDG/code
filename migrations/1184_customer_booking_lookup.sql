-- 1184_customer_booking_lookup
--
-- workshop:no-transaction
--
-- A customer's own bookings that are not over yet, read by their contact
-- (W18-LATENCY-POLISH): the assistant's list_my_bookings tool and the
-- returning customer's memory ask for them on a customer's turn, so the
-- lookup must cost the same in a business with ten bookings as in one
-- with a hundred thousand. They used to read every booking of the
-- business not over yet and pick the customer's in memory.
--
-- bookings: (business_id, doc_contact_id, doc_ends_at), the contacts of
--   one customer (the conversation's and those under the proved phone)
--   and the end of their bookings after now; the status, the sandbox flag
--   and the order by start are applied to those few rows. Both lookup
--   columns exist (doc_contact_id since 1122, doc_ends_at since 1042), so
--   no backfill is needed.
--
-- Online-safe (migrations/README.md): bookings is an existing, busy table,
-- so the index is built CONCURRENTLY, statement by statement outside a
-- transaction (the header above) and idempotent.

create index concurrently if not exists bookings_doc_contact_id_ends_at_idx
    on workshop.bookings (business_id, doc_contact_id, doc_ends_at);
