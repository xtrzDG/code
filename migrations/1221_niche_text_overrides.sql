-- 1221_niche_text_overrides
--
-- The niche template editor of the platform admin (R17-NICHE-TEMPLATE-
-- EDITOR): the niche templates stay in code; an admin rewords their
-- owner-facing texts (question labels, hints, choices, default rules,
-- starter answers) per language as a draft and publishes it as a numbered
-- version. The newest version of a niche is laid over the code template
-- for the tunnel and the profile wizard of new owners; older versions stay
-- for the history and a revert. Both tables are platform collections: they
-- name no business, so the tenant role holds no privilege on them (1200).
--
-- Online-safe (migrations/README.md): one transaction; both tables are new
-- and empty, so their lookup columns and index are built right here. No
-- existing table changes.
--
-- niche_text_drafts (platform collection): one per niche, read by its key.
-- niche_text_releases (platform collection):
--   (doc_niche_key, doc_version)   the newest version of each niche (the
--                                  tunnel and the wizard: one probe per
--                                  niche) and a niche's history, newest
--                                  first; the id, derived from the niche
--                                  and the version, keeps two admins from
--                                  storing the same version twice

select workshop.create_platform_collection('niche_text_drafts');

select workshop.create_platform_collection('niche_text_releases');
select workshop.add_lookup_column('niche_text_releases', 'niche_key', 'text');
select workshop.add_lookup_column('niche_text_releases', 'version', 'bigint');
create index if not exists niche_text_releases_doc_niche_key_version_idx
    on workshop.niche_text_releases (doc_niche_key, doc_version);
