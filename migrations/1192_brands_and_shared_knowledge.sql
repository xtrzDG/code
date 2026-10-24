-- 1192_brands_and_shared_knowledge
--
-- workshop:no-transaction
--
-- Brands: a chain of locations run by one team, with one combined view,
-- shared answers and sister-location offers (R17-BRANDS).
--
-- brands (platform collection): the brand, its team (BRAND_OWNER and
--   REGIONAL_MANAGER members, a manager with the locations assigned to
--   them) and the location that carries the brand's one setup fee.
--     members[].user_id      a signed-in person's brands (every cabinet
--                            request of a brand member and /v1/me), kept
--                            in workshop.document_lookup_keys by the
--                            sync_document_lookup_keys trigger
-- brand_knowledge_items (platform collection): the facts every location of
--   a brand shares, keyed by brand and shared key.
--     (doc_brand_id, created_at)  a brand's items, oldest first (the brand
--                                 page and every location's assembly)
-- businesses (version 7: `brand_id`): the brand a business is a location
--   of; the one source of truth of a brand's locations.
--     doc_brand_id            a brand's locations (its dashboard, its
--                             sister locations, the location prices)
--
-- Online-safe (migrations/README.md): `businesses` is an existing table, so
-- its lookup column is trigger-filled (no rewrite) and its index is built
-- CONCURRENTLY; that needs this file to run statement by statement outside
-- a transaction (the header above), so every statement is idempotent. No
-- business has a brand before this release, so the new column needs no
-- backfill. The two brand tables are new and empty.

select workshop.create_document_collection('brands');
select workshop.create_document_collection('brand_knowledge_items');

create or replace trigger brands_members_lookup_keys
    after insert or update or delete on workshop.brands
    for each row execute function workshop.sync_document_lookup_keys('members', 'user_id');

select workshop.add_lookup_column('brand_knowledge_items', 'brand_id', 'text');
create index concurrently if not exists brand_knowledge_items_doc_brand_id_idx
    on workshop.brand_knowledge_items (doc_brand_id, created_at, row_sequence);

select workshop.add_lookup_column('businesses', 'brand_id', 'text');
create index concurrently if not exists businesses_doc_brand_id_idx
    on workshop.businesses (doc_brand_id);
