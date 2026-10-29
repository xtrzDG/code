-- 1213_rented_phone_numbers
--
-- A phone number for the assistant from the cabinet (W21-PHONE-NUMBERS): the
-- owner picks a number by country, city and monthly price; the platform
-- rents it from the carrier (Twilio), imports it into the voice platform
-- (ElevenLabs) for the business's agent and gives it back when the phone
-- channel is turned off. In countries whose regulator wants the business's
-- documents, the owner asks the platform team instead.
--
-- Online-safe (migrations/README.md): one transaction; both tables are new
-- and empty, so their trigger-filled lookup columns and indexes are built
-- right here. No existing table changes: a rental month is a usage event
-- and an invoice of the new kind `number_rental` (behind the closed release
-- gate `phone_number_rental`), both in their documents.
--
-- phone_numbers (business collection): a number rented for a business.
--   (business_id, ...)                    the business's numbers (its own
--                                         column; the cabinet's phone card)
--   (doc_status, doc_billed_until)        across businesses: numbers to give
--                                         back (releasing), numbers to keep
--                                         attached to their agent (active),
--                                         rental months that began (the
--                                         rental job, by billed_until)
--   (doc_phone_number)                    across businesses: whose number a
--                                         number is (a purchase refuses one
--                                         another business holds)
-- phone_number_requests (business collection): one per business, by id.
--   (doc_status)                          across businesses: open requests
--                                         (closed once the phone channel is
--                                         connected)

select workshop.create_document_collection('phone_numbers');
select workshop.create_document_collection('phone_number_requests');

select workshop.add_lookup_column('phone_numbers', 'status', 'text');
select workshop.add_lookup_column('phone_numbers', 'phone_number', 'text');
select workshop.add_lookup_column('phone_numbers', 'billed_until', 'bigint');
create index if not exists phone_numbers_doc_status_idx
    on workshop.phone_numbers (doc_status, doc_billed_until, row_sequence);
create index if not exists phone_numbers_doc_phone_number_idx
    on workshop.phone_numbers (doc_phone_number);

select workshop.add_lookup_column('phone_number_requests', 'status', 'text');
create index if not exists phone_number_requests_doc_status_idx
    on workshop.phone_number_requests (doc_status, row_sequence);
