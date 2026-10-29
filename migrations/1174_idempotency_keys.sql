-- 1174_idempotency_keys
--
-- A retried creating request never creates a second booking, staff
-- message, checkout or assistant (docs/api-versioning.md).
--
-- idempotency_keys (platform collection): one record per Idempotency-Key a
--   signed-in user sent with a creating request, keyed by the id derived
--   from the user and the key (one read by id; the key itself is not
--   stored). It holds what the first request asked for (operation and a
--   SHA-256 fingerprint of path and body) and, once it succeeded, its
--   answer, which a retry with the same key gets back. A record lives a day.
--     (doc_expires_at)  the hourly purge of expired and released records
--
-- The table is new and empty, so its lookup column (trigger-filled, as
-- every lookup column from 1122 on) and its index are added right here.

select workshop.create_document_collection('idempotency_keys');
select workshop.add_lookup_column('idempotency_keys', 'expires_at', 'bigint');
create index if not exists idempotency_keys_doc_expires_at_idx
    on workshop.idempotency_keys (doc_expires_at);
