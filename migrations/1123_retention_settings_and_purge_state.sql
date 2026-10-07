-- 1123_retention_settings_and_purge_state
--
-- The retention engine: how long each business keeps its customers' data
-- and how far its daily purge got.
--
-- business_privacy_settings (business collection): Settings → Privacy,
--   the conversation and model-record retention of one business. Read by
--   id only (the id derives from the business), so no lookup column.
--
-- retention_purge_states (business collection): the cutoffs of the last
--   finished purge of one business and what it removed. Read by id only.
--
-- The purge itself reads only indexes that exist: conversations by
-- (business_id, doc_last_message_at) (1010), messages by
-- (business_id, doc_created_at) (1042), model turns, notes and calls by
-- their conversation (1010, 1053, 1042), leads and handoffs by
-- (business_id, doc_created_at) and bookings by (business_id, doc_ends_at)
-- (1042), missed calls and customer files by (business_id, doc_created_at)
-- (1051, 1081). Two new, empty tables: nothing existing is rewritten or
-- locked.

select workshop.create_document_collection('business_privacy_settings');
select workshop.create_document_collection('retention_purge_states');
