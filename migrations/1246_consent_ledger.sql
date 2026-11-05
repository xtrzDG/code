-- 1246_consent_ledger
--
-- The consent ledger (CONS-02; Codice privacy art. 130, GDPR art. 5(2) and
-- 7(1)): every marketing consent a customer gives or takes back is one
-- entry, with the purpose, the source and its reference (the booking's
-- page, the team in person, a STOP in a chat, the erasure), the chat it
-- covers, the exact wording's version and language, who recorded it and
-- the client's network. The contact keeps only the current state; the
-- ledger keeps the history, and outlives the customer's erasure as
-- pseudonymous proof (it names the contact by id only).
--
-- consent_records (business collection), append-only:
--   read by contact, oldest first:
--     (business_id, doc_contact_id, doc_created_at)
--                                         the customer's history (their
--                                         export)
--   and by business in write order (the business's full export, keyset
--   pages on the primary key like every collection's).
--   No role of the application may change or delete an entry: the tenant
--   role may only select and insert; a trigger refuses every UPDATE,
--   whoever runs it, and every DELETE but the platform role's, which only
--   the deletion of the whole business runs (the business's rows leave
--   with it, docs/architecture.md).
--
-- Online-safe (migrations/README.md): one transaction; the table is new
-- and empty, so its trigger-filled lookup column and index are built right
-- here. No existing table changes.

select workshop.create_document_collection('consent_records');
select workshop.add_lookup_column('consent_records', 'contact_id', 'text');
select workshop.add_lookup_column('consent_records', 'created_at', 'bigint');
create index if not exists consent_records_doc_contact_id_idx
    on workshop.consent_records (business_id, doc_contact_id, doc_created_at);

create or replace function workshop.keep_consent_records_append_only()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
begin
    if tg_op = 'DELETE' and pg_has_role(current_user, 'workshop_platform', 'MEMBER') then
        -- The deletion of the whole business (the platform pool).
        return old;
    end if;

    raise exception 'consent records are append-only'
        using errcode = 'insufficient_privilege';
end;
$function$;

comment on function workshop.keep_consent_records_append_only() is
    'Refuse every change of a consent record and every deletion but the platform role''s (the deletion of a whole business) (1246).';

create or replace trigger consent_records_append_only
    before update or delete on workshop.consent_records
    for each row execute function workshop.keep_consent_records_append_only();

revoke update, delete, truncate on workshop.consent_records from workshop_tenant;
revoke update, truncate on workshop.consent_records from workshop_platform;
