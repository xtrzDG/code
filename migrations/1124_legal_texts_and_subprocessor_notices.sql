-- 1124_legal_texts_and_subprocessor_notices
--
-- The platform's own legal texts and the sub-processor list (DPA section 8)
-- with its change notices to owners (section 8.3).
--
-- subprocessor_notices (business collection): the notice each business
--   got about one addition or removal of a sub-processor, sent by the
--   daily send_subprocessor_notices job 30 days before the change. The id
--   derives from the business and the change, so the primary key keeps a
--   business to one notice per change across restarts and workers; read
--   by that id only, so no lookup column.
-- subprocessor_announcements (platform collection): each change's
--   announcement to the platform, started when its notice period opens
--   and completed once every business that existed then was told. Read by
--   its id (derived from the change) only.
--
-- users (version 3) gain optional fields nobody queries by: the terms of
-- service version accepted at sign-in and when.

select workshop.create_document_collection('subprocessor_notices');
select workshop.create_document_collection('subprocessor_announcements');
