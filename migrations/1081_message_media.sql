-- 1081_message_media
--
-- Voice notes and photos customers send in WhatsApp, Telegram, Instagram
-- and Messenger. The files themselves are kept encrypted with the
-- business's key in the media storage (the recordings' EU bucket); this
-- table keeps one row per stored file: the message it belongs to, its
-- storage path, media type, size, length and the voice note's transcript.
--
-- message_media: id derived from the inbox event and the attachment's
--   position (a turn that runs again finds its file), read by id (the
--   cabinet opens a file, the worker reuses a transcript) and by age per
--   business (the retention purge removes files older than the business's
--   recording_retention_days): (business_id, doc_created_at).
--
-- The rows belong to one business and get the usual row-level security. A
-- plain generated column, as in 1010 and 1042 (forced row-level security
-- uses an index only for leakproof conditions on plain columns).

select workshop.create_document_collection('message_media');

alter table workshop.message_media
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists message_media_doc_created_at_idx
    on workshop.message_media (business_id, doc_created_at);
