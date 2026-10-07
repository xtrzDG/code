-- 1122_online_lookup_columns
--
-- workshop:no-transaction
--
-- The first migration in the online-safe pattern (migrations/README.md):
-- lookup fields on existing tables become plain nullable columns that a
-- BEFORE INSERT OR UPDATE trigger fills from `document`, instead of stored
-- generated columns. Adding a nullable column without a default changes
-- only the catalog (no table rewrite, an ACCESS EXCLUSIVE lock held for
-- milliseconds and bounded by the runner's lock_timeout); rows written
-- before it get their values from `workshop backfill-lookup` in keyset
-- batches after the deploy; the indexes are built CONCURRENTLY, so writes
-- go on while they build. This file runs statement by statement outside a
-- transaction (the header above), so every statement is idempotent: a
-- failed try runs the file again from the top.
--
-- Fields (app/utilities/storage/document_lookup_catalog.py):
--   contacts        last_seen_at, display_name_folded  the customer list by
--                   last activity and the exact-name search
--   knowledge_items updated_at, is_active             the knowledge list
--   bookings, leads contact_id, source_channel        a contact page's counts
--
-- And one new collection, client_standings: the platform admin's client
-- list as a periodic job ranks it (a new, empty table, so its lookup
-- columns and indexes cost nothing to add; they use the same trigger).
--
-- A plain (not generated) column `doc_<field>` of a collection table is a
-- trigger-filled lookup column of the document field <field>: the trigger's
-- arguments, `workshop backfill-lookup` and the tests read them from the
-- catalog by that rule, so there is no registry to keep in step.

-- Copies document fields into their columns. Arguments: pairs of (column,
-- document field). jsonb_populate_record converts like the generated
-- columns' casts did: a JSON number into bigint, a string, enum value or
-- boolean ("true") into text; a missing field gives NULL, and a value of
-- the wrong type fails the write.
create or replace function workshop.fill_lookup_columns()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
declare
    lookup_values jsonb := '{}'::jsonb;
    argument_index integer := 0;
begin
    while argument_index < tg_nargs loop
        lookup_values := lookup_values || jsonb_build_object(
            tg_argv[argument_index], new.document -> tg_argv[argument_index + 1]
        );
        argument_index := argument_index + 2;
    end loop;
    new := jsonb_populate_record(new, lookup_values);
    return new;
end;
$function$;

comment on function workshop.fill_lookup_columns() is
    'Fill the trigger-kept lookup columns of a row from its document (pairs of column, field).';

-- Adds one trigger-filled lookup column `doc_<field>` and (re)creates the
-- table's `<table>_lookup_columns` trigger over all of them.
-- Both steps are short catalog changes; the caller's lock_timeout bounds
-- their lock waits. Safe to call again.
create or replace function workshop.add_lookup_column(
    collection_name text,
    field_name text,
    column_type text
)
returns void
language plpgsql
set search_path = pg_catalog
as $function$
declare
    lookup_column text := 'doc_' || field_name;
    trigger_arguments text;
begin
    if collection_name !~ '^[a-z][a-z0-9_]{1,62}$'
        or field_name !~ '^[a-z][a-z0-9_]{0,58}$' then
        raise exception 'invalid lookup column %.%', collection_name, field_name
            using errcode = 'invalid_name';
    end if;

    if column_type not in ('text', 'bigint') then
        raise exception 'lookup columns are text or bigint, not %', column_type
            using errcode = 'invalid_parameter_value';
    end if;

    execute format(
        'alter table workshop.%I add column if not exists %I %s',
        collection_name, lookup_column, column_type
    );
    select string_agg(
        format('%L, %L', attribute.attname, substr(attribute.attname, 5)),
        ', ' order by attribute.attname
    )
    into trigger_arguments
    from pg_attribute as attribute
    where attribute.attrelid = format('workshop.%I', collection_name)::regclass
        and attribute.attname like 'doc\_%'
        and attribute.attgenerated = ''
        and attribute.attnum > 0
        and not attribute.attisdropped;

    execute format(
        'create or replace trigger %I before insert or update of document '
        'on workshop.%I for each row execute function '
        'workshop.fill_lookup_columns(%s)',
        collection_name || '_lookup_columns', collection_name, trigger_arguments
    );
end;
$function$;

comment on function workshop.add_lookup_column(text, text, text) is
    'Add a trigger-filled lookup column doc_<field> to a document collection (no table rewrite).';

select workshop.add_lookup_column('contacts', 'last_seen_at', 'bigint');
select workshop.add_lookup_column('contacts', 'display_name_folded', 'text');
select workshop.add_lookup_column('knowledge_items', 'updated_at', 'bigint');
select workshop.add_lookup_column('knowledge_items', 'is_active', 'text');
select workshop.add_lookup_column('bookings', 'contact_id', 'text');
select workshop.add_lookup_column('bookings', 'source_channel', 'text');
select workshop.add_lookup_column('leads', 'contact_id', 'text');
select workshop.add_lookup_column('leads', 'source_channel', 'text');

select workshop.create_document_collection('client_standings');
select workshop.add_lookup_column('client_standings', 'business_status', 'text');
select workshop.add_lookup_column('client_standings', 'health_status', 'text');
select workshop.add_lookup_column('client_standings', 'country_code', 'text');
select workshop.add_lookup_column('client_standings', 'niche_key', 'text');
select workshop.add_lookup_column('client_standings', 'is_losing_money', 'text');
select workshop.add_lookup_column('client_standings', 'health_position', 'bigint');
select workshop.add_lookup_column('client_standings', 'name_position', 'bigint');
select workshop.add_lookup_column('client_standings', 'usage_position', 'bigint');
select workshop.add_lookup_column('client_standings', 'margin_position', 'bigint');
select workshop.add_lookup_column('client_standings', 'cost_position', 'bigint');
select workshop.add_lookup_column('client_standings', 'revenue_position', 'bigint');

-- The customer list, most recently active first, and the exact-name search.
create index concurrently if not exists contacts_doc_last_seen_at_idx
    on workshop.contacts (business_id, doc_last_seen_at, created_at, row_sequence);
create index concurrently if not exists contacts_doc_display_name_folded_idx
    on workshop.contacts (business_id, doc_display_name_folded);

-- The knowledge list, last changed first, of every kind or of one.
create index concurrently if not exists knowledge_items_doc_updated_at_idx
    on workshop.knowledge_items (business_id, doc_updated_at, created_at, row_sequence);
create index concurrently if not exists knowledge_items_doc_kind_updated_at_idx
    on workshop.knowledge_items
        (business_id, doc_kind, doc_updated_at, created_at, row_sequence);

-- The bookings and leads of the customers on one page of the list.
create index concurrently if not exists bookings_doc_contact_id_idx
    on workshop.bookings (business_id, doc_contact_id);
create index concurrently if not exists leads_doc_contact_id_idx
    on workshop.leads (business_id, doc_contact_id);

-- The platform admin's client list (platform-wide): one order of the list
-- each, and the filters it counts by.
create index concurrently if not exists client_standings_doc_health_position_idx
    on workshop.client_standings (doc_health_position, created_at, row_sequence);
create index concurrently if not exists client_standings_doc_name_position_idx
    on workshop.client_standings (doc_name_position, created_at, row_sequence);
create index concurrently if not exists client_standings_doc_usage_position_idx
    on workshop.client_standings (doc_usage_position, created_at, row_sequence);
create index concurrently if not exists client_standings_doc_margin_position_idx
    on workshop.client_standings (doc_margin_position, created_at, row_sequence);
create index concurrently if not exists client_standings_doc_cost_position_idx
    on workshop.client_standings (doc_cost_position, created_at, row_sequence);
create index concurrently if not exists client_standings_doc_revenue_position_idx
    on workshop.client_standings (doc_revenue_position, created_at, row_sequence);
create index concurrently if not exists client_standings_doc_business_status_idx
    on workshop.client_standings (doc_business_status);
create index concurrently if not exists client_standings_doc_health_status_idx
    on workshop.client_standings (doc_health_status);
create index concurrently if not exists client_standings_doc_country_code_idx
    on workshop.client_standings (doc_country_code);
create index concurrently if not exists client_standings_doc_niche_key_idx
    on workshop.client_standings (doc_niche_key);
