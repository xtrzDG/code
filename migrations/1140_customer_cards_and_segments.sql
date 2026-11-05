-- 1140_customer_cards_and_segments
--
-- Customers (R11-CUSTOMERS-SEARCH): the team's card on a customer, saved
-- segments and the team's customer settings. Online-safe
-- (migrations/README.md): one transaction of catalog changes only, every
-- statement idempotent; nothing in it rewrites, scans or locks a busy
-- table for longer than a catalog change (the runner's lock_timeout bounds
-- the wait), and it builds no index (the filter columns narrow a page the
-- last-activity index already reads; the tag keys share the lookup key
-- table's index).
--
-- contacts (version 4): the card fields
--   tags[].key   kept in workshop.document_lookup_keys by the
--                contacts_tags_lookup_keys trigger (the list's tag filter,
--                a segment's tag rule); rows written before this file have
--                no tags, so there is nothing to backfill
--   (doc_is_vip, doc_is_blocked)  trigger-filled FILTER_TEXT columns that
--                narrow the customer list's last-activity page ("VIP",
--                "Blocked"); only rows written from this release on can be
--                VIP or blocked, so a missing value in older rows is right
--
-- customer_segments (business collection): the owner's saved segments, a
--   few per business, read by business only.
-- customer_settings (business collection): one document per business,
--   read by its derived id.

select workshop.create_document_collection('customer_segments');
select workshop.create_document_collection('customer_settings');

select workshop.add_lookup_column('contacts', 'is_vip', 'text');
select workshop.add_lookup_column('contacts', 'is_blocked', 'text');

create or replace trigger contacts_tags_lookup_keys
    after insert or update or delete on workshop.contacts
    for each row execute function workshop.sync_document_lookup_keys('tags', 'key');
