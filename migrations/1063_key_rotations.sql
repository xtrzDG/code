-- 1063_key_rotations
--
-- Key management: the latest re-encryption of the stored secrets (channel
-- credentials, Google Calendar tokens) with the current key of the ring
-- (ENCRYPTION_KEYS). A platform collection (no business) holding one
-- document, found by its fixed key; earlier runs live on in the audit log
-- (entity `encryption_keys`). Row-level security as on every collection:
-- only the platform-wide scope reads it.

select workshop.create_document_collection('key_rotations');
