-- 1103_sessions_and_support_access
--
-- Device sessions, the platform admin team and platform support's
-- time-boxed, consented access to a client's cabinet.
--
-- user_sessions (platform collection) gain, in schema version 3, the
--   device (`user_agent`, `created_ip`), its last use (`last_seen_at`,
--   `last_seen_ip`) and `idle_expires_at`; two of them are queried:
--     doc_user_id          a person's sessions (Account → Security, "sign
--                          out everywhere else")
--     doc_idle_expires_at  the daily purge of sessions unused too long
--
-- platform_admins (platform collection, no business): who may open the
--   admin pages and with which role (SUPER, SUPPORT_READONLY, BILLING).
--   Read at every admin request by the person's sign-in destination:
--     doc_phone_number, doc_email  the record of a signed-in person
--     doc_role                     is a SUPER admin recorded? (the
--                                  PLATFORM_ADMIN_* lists only bootstrap
--                                  the first one)
--
-- support_access_grants (business collection): a platform admin's hour
--   of read-only access to one business, opened with a reason, and the
--   owner's expiring consent that support may also change things. Kept
--   apart from businesses so access never rewrites the business row.
--     (business_id, doc_status)        the open grants of a business (its
--                                      banner, every support request)
--     (business_id, doc_admin_user_id) one admin's grants in a business
--     (doc_status)                     the open grants everywhere: the
--                                      periodic job ending expired ones
--
-- Plain generated columns, as in 1010 and 1042 (forced row-level security
-- uses an index only for leakproof conditions on plain columns). Adding
-- the stored columns rewrites user_sessions once (one row per signed-in
-- device; expired rows are purged daily).

select workshop.create_document_collection('platform_admins');
select workshop.create_document_collection('support_access_grants');

alter table workshop.user_sessions
    add column if not exists doc_user_id text
        generated always as (document ->> 'user_id') stored,
    add column if not exists doc_idle_expires_at bigint
        generated always as ((document ->> 'idle_expires_at')::bigint) stored;
create index if not exists user_sessions_doc_user_id_idx
    on workshop.user_sessions (doc_user_id);
create index if not exists user_sessions_doc_idle_expires_at_idx
    on workshop.user_sessions (doc_idle_expires_at);

alter table workshop.platform_admins
    add column if not exists doc_phone_number text
        generated always as (document ->> 'phone_number') stored,
    add column if not exists doc_email text
        generated always as (document ->> 'email') stored,
    add column if not exists doc_role text
        generated always as (document ->> 'role') stored;
create index if not exists platform_admins_doc_phone_number_idx
    on workshop.platform_admins (doc_phone_number);
create index if not exists platform_admins_doc_email_idx
    on workshop.platform_admins (doc_email);
create index if not exists platform_admins_doc_role_idx
    on workshop.platform_admins (doc_role);

alter table workshop.support_access_grants
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored,
    add column if not exists doc_admin_user_id text
        generated always as (document ->> 'admin_user_id') stored;
create index if not exists support_access_grants_doc_status_idx
    on workshop.support_access_grants (business_id, doc_status);
create index if not exists support_access_grants_doc_admin_user_id_idx
    on workshop.support_access_grants (business_id, doc_admin_user_id);
create index if not exists support_access_grants_doc_status_platform_idx
    on workshop.support_access_grants (doc_status);
