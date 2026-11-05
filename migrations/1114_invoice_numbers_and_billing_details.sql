-- 1114_invoice_numbers_and_billing_details
--
-- Invoices an accountant can file: numbered, with the buyer's billing
-- details and the VAT.
--
-- billing_profiles (business collection): the details a business wants on
--   its invoices (registered name, tax number, address, billing e-mail,
--   country). One row per business, read by its derived key only, so it
--   needs no lookup column.
--
-- invoice_counters (platform collection, no business): the last number of
--   each invoice series and year ("AW:2026"). A number is taken by
--   compare-and-set on the row (read, then replace only if `last_number`
--   is still the one read), so concurrent issuers never share a number.
--   Read by its key only.
--
-- invoices gain, in schema version 2, `number`, the `seller` and `buyer`
-- copies, the tax lines, `paid_at` and the masked card: fields inside the
-- document, nothing to index.

select workshop.create_document_collection('billing_profiles');
select workshop.create_document_collection('invoice_counters');
