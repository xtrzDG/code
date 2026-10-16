-- 1134_export_download_links
--
-- Full business exports are downloaded only through one-time links.
--
-- export_download_links (business collection): one link an owner asked
--   for after a recent sign-in or step-up. Only the SHA-256 of its token is
--   stored, and the id derives from that hash, so a download finds its link
--   by one read by id. A link works once (`used_at`), for ten minutes at
--   most, and only with a session of the owner it was made for.
--     (doc_expires_at)  the hourly purge of expired links, across businesses
--
-- business_exports (version 2) gain `download_count` (at most three
-- downloads per export), a field nobody queries by.
--
-- The table is new and empty, so its lookup column (trigger-filled, as
-- every lookup column from 1122 on) and its index are added right here.

select workshop.create_document_collection('export_download_links');
select workshop.add_lookup_column('export_download_links', 'expires_at', 'bigint');
create index if not exists export_download_links_doc_expires_at_idx
    on workshop.export_download_links (doc_expires_at);
