-- 1082_two_factor_sign_in
--
-- Two-factor sign-in (TOTP authenticators and recovery codes), required
-- for platform admins and, when the owner asks for it, for a business's
-- team; sensitive actions confirm the person again (step-up).
--
-- totp_factors: a user's authenticator app, its secret sealed with the
--   key ring; at most one per user, found by (doc_user_id) at every sign-in
--   of a user who has one and every step-up.
-- recovery_codes: single-use codes of a user with an authenticator, only
--   their keyed hashes; read and replaced by (doc_user_id).
-- mfa_challenges: the second step of one sign-in (five minutes); read by
--   id, purged by age: (doc_created_at).
--
-- Platform collections (no business): the documents carry no business_id.
-- user_sessions gain the optional `auth_level` and `authenticated_at`
-- (schema version 2) and businesses the optional `require_mfa_for_members`
-- (schema version 4); nobody queries by them, so no columns.
--
-- Plain generated columns, as in 1010 and 1042 (forced row-level security
-- uses an index only for leakproof conditions on plain columns).

select workshop.create_document_collection('totp_factors');
select workshop.create_document_collection('recovery_codes');
select workshop.create_document_collection('mfa_challenges');

alter table workshop.totp_factors
    add column if not exists doc_user_id text
        generated always as (document ->> 'user_id') stored;
create index if not exists totp_factors_doc_user_id_idx
    on workshop.totp_factors (doc_user_id);

alter table workshop.recovery_codes
    add column if not exists doc_user_id text
        generated always as (document ->> 'user_id') stored;
create index if not exists recovery_codes_doc_user_id_idx
    on workshop.recovery_codes (doc_user_id);

alter table workshop.mfa_challenges
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists mfa_challenges_doc_created_at_idx
    on workshop.mfa_challenges (doc_created_at);
