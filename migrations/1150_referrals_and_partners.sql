-- 1150_referrals_and_partners
--
-- The referral and partner program (R15-REFERRALS): owners invite owners,
-- partners bring businesses, and every chat, hosted page and table card
-- carries a "Powered by" link with the business's code.
--
-- partners (platform collection): agencies and consultants with their
--   commission rate, named by the phone number or e-mail they sign in
--   with.
--     doc_phone_number, doc_email  the partner of a signed-in person
--     doc_status                   the admin's list (active, paused)
--
-- referral_codes (platform collection): a code and whose it is, keyed by
--   the code in lower case (one code, one owner). A business's own code
--   carries its business id (the row belongs to it); a partner's does not.
--     doc_partner_id               a partner's codes
--
-- referrals (platform collection): each business that signed up by a
--   code, once. An owner's invitation belongs to the inviting business
--   (its owner counts them through the business index); a partner's
--   referral belongs to no business.
--     (doc_partner_id, doc_referred_at)    a partner's businesses, newest first
--     (doc_partner_id, doc_first_paid_at)  how many of them have paid
--
-- commission_entries (business collection: the row belongs to the paying
--   business): a partner's commission on one paid invoice, keyed by the
--   invoice.
--     (doc_partner_id, doc_accrued_at)   a partner's commissions, newest first
--     (doc_month, doc_partner_id, doc_status, doc_currency_code,
--      doc_amount_minor)                 a payout month summed per partner,
--                                        status and currency from the index
--
-- businesses (version 6: `referred_by`, `hides_powered_by`) and
-- billing_credits (version 2: `referral_of`) gain optional fields nobody
-- queries by: no column, no index.
--
-- The tables are new and empty, so their lookup columns (trigger-filled)
-- and indexes are added right here.

select workshop.create_document_collection('partners');
select workshop.create_document_collection('referral_codes');
select workshop.create_document_collection('referrals');
select workshop.create_document_collection('commission_entries');

select workshop.add_lookup_column('partners', 'phone_number', 'text');
select workshop.add_lookup_column('partners', 'email', 'text');
select workshop.add_lookup_column('partners', 'status', 'text');
create index if not exists partners_doc_phone_number_idx
    on workshop.partners (doc_phone_number);
create index if not exists partners_doc_email_idx
    on workshop.partners (doc_email);
create index if not exists partners_doc_status_idx
    on workshop.partners (doc_status, created_at, row_sequence);

select workshop.add_lookup_column('referral_codes', 'partner_id', 'text');
create index if not exists referral_codes_doc_partner_id_idx
    on workshop.referral_codes (doc_partner_id);

select workshop.add_lookup_column('referrals', 'partner_id', 'text');
select workshop.add_lookup_column('referrals', 'referred_at', 'bigint');
select workshop.add_lookup_column('referrals', 'first_paid_at', 'bigint');
create index if not exists referrals_doc_partner_id_idx
    on workshop.referrals (doc_partner_id, doc_referred_at, row_sequence);
create index if not exists referrals_doc_first_paid_at_idx
    on workshop.referrals (doc_partner_id, doc_first_paid_at);

select workshop.add_lookup_column('commission_entries', 'partner_id', 'text');
select workshop.add_lookup_column('commission_entries', 'month', 'text');
select workshop.add_lookup_column('commission_entries', 'status', 'text');
select workshop.add_lookup_column('commission_entries', 'currency_code', 'text');
select workshop.add_lookup_column('commission_entries', 'accrued_at', 'bigint');
select workshop.add_lookup_column('commission_entries', 'amount_minor', 'bigint');
create index if not exists commission_entries_doc_partner_id_idx
    on workshop.commission_entries (doc_partner_id, doc_accrued_at, row_sequence);
create index if not exists commission_entries_doc_month_idx
    on workshop.commission_entries
    (doc_month, doc_partner_id, doc_status, doc_currency_code, doc_amount_minor);
