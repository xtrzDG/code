-- 1160_two_way_availability
--
-- Two-way availability (R13-CALENDAR-SYNC): calendars outside the
-- platform block a resource's slots, and a resource's bookings are offered
-- back as an iCal feed. Online-safe (migrations/README.md): one
-- transaction; the three tables are new and empty, so their lookup column
-- (trigger-filled, as every lookup column from 1122 on) and index are built
-- right here. ResourceDocument's new `external_calendar_id` lives in the
-- stored document only: no column, nothing to backfill.
--
-- resource_calendar_links (business collection): one document per
--   resource, read by id; (doc_next_sync_at) finds the resources whose
--   calendars are due across businesses (the five-minute sync job).
-- calendar_busy_times (business collection): one document per resource
--   and source, read by id, and every one of a business by business_id
--   (the table's own index) when a booking is placed.
-- ical_export_feeds (business collection): one document per export
--   address, read by its key, the hash of the address's token.

select workshop.create_document_collection('resource_calendar_links');
select workshop.create_document_collection('calendar_busy_times');
select workshop.create_document_collection('ical_export_feeds');

select workshop.add_lookup_column('resource_calendar_links', 'next_sync_at', 'bigint');
create index if not exists resource_calendar_links_doc_next_sync_at_idx
    on workshop.resource_calendar_links (doc_next_sync_at);
