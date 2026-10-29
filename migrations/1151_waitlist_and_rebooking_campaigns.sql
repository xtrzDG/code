-- 1151_waitlist_and_rebooking_campaigns
--
-- Revenue features (W17-WAITLIST-REBOOKING): a waitlist that fills the
-- places cancellations and moves free, and rebooking campaigns the owner
-- turns on. Online-safe (migrations/README.md): one transaction; the four
-- tables are new and empty, so their lookup columns (trigger-filled, as
-- every lookup column from 1122 on) and indexes are built right here; on
-- bookings, an existing table, it only adds a trigger-filled column and
-- builds no index.
--
-- waitlist_entries (business collection): one customer's place on the list.
--   (business_id, doc_status, doc_created_at)  the cabinet's list by status,
--                                              first come first, and the
--                                              first waiting entry a freed
--                                              place goes to
--   (business_id, doc_contact_id)              a customer's open entries
--                                              (their yes or no, a new join)
--   (doc_status, doc_offer_expires_at)         across businesses: offers
--                                              whose hold ran out (the sweep)
--   (doc_status, doc_waits_until)              across businesses: entries
--                                              whose day passed (the sweep)
-- waitlist_settings (business collection): one document per business, by id.
-- campaign_settings (business collection): one document per business, by
--   id; (doc_is_enabled) finds the businesses whose campaign is on, across
--   businesses, for the hourly job.
-- campaign_messages (business collection): one message of a campaign.
--   (business_id, doc_month, doc_status)       the monthly cap's count
--   (business_id, doc_status, doc_sent_at)     invitations still waiting
--                                              for a booking (attribution)
--   (business_id, doc_created_at)              the cabinet's latest first
--   (business_id, doc_contact_id)              a customer's messages
--
-- bookings (version 4): (doc_origin), a trigger-filled FILTER_TEXT column
--   that narrows the value model's grouped counts of a period (the
--   creation-time index reads the period). Rows written before this file
--   come from neither the waitlist nor a campaign, so a missing value in
--   them is right: nothing to backfill.

select workshop.create_document_collection('waitlist_entries');
select workshop.create_document_collection('waitlist_settings');
select workshop.create_document_collection('campaign_settings');
select workshop.create_document_collection('campaign_messages');

select workshop.add_lookup_column('waitlist_entries', 'contact_id', 'text');
select workshop.add_lookup_column('waitlist_entries', 'status', 'text');
select workshop.add_lookup_column('waitlist_entries', 'created_at', 'bigint');
select workshop.add_lookup_column('waitlist_entries', 'offer_expires_at', 'bigint');
select workshop.add_lookup_column('waitlist_entries', 'waits_until', 'bigint');
select workshop.add_lookup_column('waitlist_entries', 'is_sandbox', 'text');
create index if not exists waitlist_entries_doc_status_idx
    on workshop.waitlist_entries (business_id, doc_status, doc_created_at, row_sequence);
create index if not exists waitlist_entries_doc_contact_id_idx
    on workshop.waitlist_entries (business_id, doc_contact_id);
create index if not exists waitlist_entries_doc_offer_expires_at_idx
    on workshop.waitlist_entries (doc_status, doc_offer_expires_at);
create index if not exists waitlist_entries_doc_waits_until_idx
    on workshop.waitlist_entries (doc_status, doc_waits_until);

select workshop.add_lookup_column('campaign_settings', 'is_enabled', 'text');
create index if not exists campaign_settings_doc_is_enabled_idx
    on workshop.campaign_settings (doc_is_enabled);

select workshop.add_lookup_column('campaign_messages', 'contact_id', 'text');
select workshop.add_lookup_column('campaign_messages', 'status', 'text');
select workshop.add_lookup_column('campaign_messages', 'month', 'text');
select workshop.add_lookup_column('campaign_messages', 'sent_at', 'bigint');
select workshop.add_lookup_column('campaign_messages', 'created_at', 'bigint');
create index if not exists campaign_messages_doc_month_idx
    on workshop.campaign_messages (business_id, doc_month, doc_status);
create index if not exists campaign_messages_doc_sent_at_idx
    on workshop.campaign_messages (business_id, doc_status, doc_sent_at);
create index if not exists campaign_messages_doc_created_at_idx
    on workshop.campaign_messages (business_id, doc_created_at, row_sequence);
create index if not exists campaign_messages_doc_contact_id_idx
    on workshop.campaign_messages (business_id, doc_contact_id);

select workshop.add_lookup_column('bookings', 'origin', 'text');
