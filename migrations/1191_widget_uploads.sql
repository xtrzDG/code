-- 1191_widget_uploads
--
-- Photos and voice notes website chat visitors send (W19-WIDGET-MEDIA-
-- RATING): the widget uploads the file first and its message names it.
--
-- widget_uploads (business collection): one row per uploaded file, checked
--   when it came (its bytes are the type the browser declared, under the
--   cap of its kind, a photo without its metadata, a voice note's length
--   read from its container) and kept encrypted with the business's key in
--   the media storage. Read by id (the message names it; it is claimed
--   once, by the visitor who uploaded it), and by age per business:
--     (business_id, doc_created_at)  the daily purge of uploads older than
--                                    a day, attached or not (the message's
--                                    own copy keeps the business's
--                                    retention)
--
-- The rows belong to one business and get the usual row-level security.
-- The table is new and empty, so its lookup column (trigger-filled, as
-- every lookup column from 1122 on) and its index are added right here.

select workshop.create_document_collection('widget_uploads');
select workshop.add_lookup_column('widget_uploads', 'created_at', 'bigint');
create index if not exists widget_uploads_doc_created_at_idx
    on workshop.widget_uploads (business_id, doc_created_at);
