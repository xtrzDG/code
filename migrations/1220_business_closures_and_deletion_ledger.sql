-- 1220_business_closures_and_deletion_ledger
--
-- Closing a business and deleting it (R15-ACCOUNT-DELETION): an owner
-- closes a business (or its subscription ended unpaid OFFBOARD_AFTER_DAYS
-- ago); for 30 days it is pending deletion (the assistant paused, the
-- channels off, the full export offered, the closure cancellable); then a
-- job of the platform pool switches off what the business had at the
-- providers, queues the sub-processors' erasure and deletes every row and
-- file of the business. The deletion ledger records each deletion: its
-- owners download the certificate from it, and the restore drill and a
-- daily job apply it to a restored database (with its copy outside the
-- database, in the backup bucket), so a restored backup never brings a
-- deleted business back.
--
-- Online-safe (migrations/README.md): one transaction; both tables are new
-- and empty, so their trigger-filled lookup columns and indexes are built
-- right here. No existing table changes.
--
-- business_closures (business collection): one per business, read by id.
--   (doc_delete_after)                    across businesses: the closures
--                                         whose deletion is due (the hourly
--                                         sweep, platform-wide)
-- business_deletions (platform collection, the deletion ledger; the
--   business it records is named in the document, never in the business
--   column, so the tenant role never sees it):
--   read by id (derived from the business: the deletion job, the
--   certificate);
--   owners[].user_id                      a person's entries (Account: the
--                                         certificates of closed
--                                         businesses), kept in
--                                         workshop.document_lookup_keys by
--                                         the sync_document_lookup_keys
--                                         trigger
--   (doc_started_at)                      every entry in the order the
--                                         deletions began (the daily job
--                                         that applies the ledger again
--                                         after a restore)

select workshop.create_document_collection('business_closures');
select workshop.add_lookup_column('business_closures', 'delete_after', 'bigint');
create index if not exists business_closures_doc_delete_after_idx
    on workshop.business_closures (doc_delete_after, row_sequence);

select workshop.create_platform_collection('business_deletions');
select workshop.add_lookup_column('business_deletions', 'started_at', 'bigint');
create index if not exists business_deletions_doc_started_at_idx
    on workshop.business_deletions (doc_started_at, row_sequence);
create or replace trigger business_deletions_owners_lookup_keys
    after insert or update or delete on workshop.business_deletions
    for each row execute function workshop.sync_document_lookup_keys('owners', 'user_id');
