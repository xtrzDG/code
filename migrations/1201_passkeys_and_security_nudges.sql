-- 1201_passkeys_and_security_nudges
--
-- W20-PASSKEYS-CSP: passkeys (WebAuthn) as a phishing-resistant second
-- factor of the sign-in and of step-up confirmations, and the owner's
-- reminder to protect their customers' data with a second factor.
--
-- passkeys (platform collection, no business): a person's passkeys, each
--   stored under an id derived from its credential id, so one credential
--   is one passkey whoever adds it (`insert_if_absent` on the key). The
--   public key and the signature counter it last reported; never a
--   secret. Read by id, and a person's list by
--     (doc_user_id)          Account → Security, the second step of a
--                            sign-in and step-up (a handful per person)
-- passkey_challenges (platform collection, no business): the random
--   challenge of one ceremony (five minutes, consumed by compare-and-swap,
--   so a signed answer counts once). Read by id, purged by age:
--     (doc_created_at)       the daily purge of stale rows
-- security_nudges (business collection: row-level security by business):
--   one document per person and business, under an id derived from both:
--   when the owner put away the "turn on a second factor" banner, and how
--   many people the team had then (the banner comes back once the team
--   grows past one). Read by id only.
--
-- The two platform collections are made with create_platform_collection
-- (1200): their rows name no business, so the tenant role holds nothing
-- on them; security_nudges gets the tenant and platform policies of every
-- business collection from create_document_collection.
--
-- The tables are new and empty, so their lookup columns (trigger-filled,
-- as every lookup column from 1122 on) and indexes are added right here.

select workshop.create_platform_collection('passkeys');
select workshop.add_lookup_column('passkeys', 'user_id', 'text');
create index if not exists passkeys_doc_user_id_idx
    on workshop.passkeys (doc_user_id);

select workshop.create_platform_collection('passkey_challenges');
select workshop.add_lookup_column('passkey_challenges', 'created_at', 'bigint');
create index if not exists passkey_challenges_doc_created_at_idx
    on workshop.passkey_challenges (doc_created_at);

select workshop.create_document_collection('security_nudges');
