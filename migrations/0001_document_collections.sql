-- 0001_document_collections
--
-- Document storage of Assistant Workshop (concept: technical specification,
-- sections 2 "tables" and 10 "RLS on every table"). Postgres runs in the EU.
--
-- Every document collection is one table in the schema "workshop" (kept out
-- of "public", which hosted Postgres products expose through their data API):
--
--   document_key  text primary key   storage key (usually the document id)
--   business_id   text               owning business, copied from the document
--                                    (null for platform documents such as users)
--   document      jsonb not null     the document as Pydantic serializes it
--   created_at    bigint not null    first write, UNIX microseconds
--   updated_at    bigint not null    last write, UNIX microseconds
--   row_sequence  bigint identity    keeps the first-write order stable
--
-- Business isolation. Repositories already read tenant documents only
-- together with their business id; row-level security is the second line
-- of defence. RLS is enabled and FORCED on every collection table (so it
-- also binds the owning role), with one policy for reads and writes:
--
--   business_id = current_setting('app.business_id', true)
--   or current_setting('app.bypass_rls', true) = 'on'
--
-- The application sets both values per transaction (set_config(..., true),
-- the parameterized SET LOCAL): one business for requests scoped to it, or
-- the platform bypass for webhook routing, sign-in, admin views and
-- background jobs. A session without settings sees and writes nothing.
-- Connect the application with a role that is neither superuser nor
-- BYPASSRLS; such roles skip every policy. If migrations run as another role
-- than the application, grant the application role usage on the schema and
-- select, insert, update, delete on the tables.
--
-- Later migrations add a collection with one line:
--   select workshop.create_document_collection('new_collection_name');

create schema if not exists workshop;

create or replace function workshop.create_document_collection(collection_name text)
returns void
language plpgsql
set search_path = pg_catalog
as $function$
declare
    qualified_table text := format('workshop.%I', collection_name);
begin
    if collection_name !~ '^[a-z][a-z0-9_]{1,62}$' then
        raise exception 'invalid document collection name: %', collection_name
            using errcode = 'invalid_name';
    end if;

    execute format(
        'create table if not exists %s ('
        '    document_key text primary key,'
        '    business_id text,'
        '    document jsonb not null,'
        '    created_at bigint not null,'
        '    updated_at bigint not null,'
        '    row_sequence bigint generated always as identity'
        ')',
        qualified_table
    );
    execute format(
        'create index if not exists %I on %s (business_id, created_at, row_sequence)',
        collection_name || '_business_idx',
        qualified_table
    );
    execute format(
        'create index if not exists %I on %s (created_at, row_sequence)',
        collection_name || '_order_idx',
        qualified_table
    );
    execute format('alter table %s enable row level security', qualified_table);
    execute format('alter table %s force row level security', qualified_table);
    execute format('drop policy if exists business_isolation on %s', qualified_table);
    execute format(
        'create policy business_isolation on %s'
        ' using ('
        '     business_id = current_setting(''app.business_id'', true)'
        '     or current_setting(''app.bypass_rls'', true) = ''on'''
        ' )'
        ' with check ('
        '     business_id = current_setting(''app.business_id'', true)'
        '     or current_setting(''app.bypass_rls'', true) = ''on'''
        ' )',
        qualified_table
    );
end;
$function$;

comment on function workshop.create_document_collection(text) is
    'Create or update the table, indexes and row-level security of one document collection.';

-- Users and sign-in (platform-wide: no business).
select workshop.create_document_collection('users');
select workshop.create_document_collection('otp_challenges');
select workshop.create_document_collection('user_sessions');

-- Businesses (a business row carries its own id as business_id), profiles,
-- channels.
select workshop.create_document_collection('businesses');
select workshop.create_document_collection('business_profiles');
select workshop.create_document_collection('channels');

-- Knowledge, resources and schedules.
select workshop.create_document_collection('knowledge_items');
select workshop.create_document_collection('resources');
select workshop.create_document_collection('schedule_exceptions');

-- Customers and conversations.
select workshop.create_document_collection('contacts');
select workshop.create_document_collection('conversations');
select workshop.create_document_collection('messages');
select workshop.create_document_collection('llm_turns');
select workshop.create_document_collection('calls');

-- Bookings, leads, handoffs and open questions.
select workshop.create_document_collection('bookings');
select workshop.create_document_collection('leads');
select workshop.create_document_collection('handoffs');
select workshop.create_document_collection('unanswered_questions');

-- Assistant versions and autotests.
select workshop.create_document_collection('assistant_versions');
select workshop.create_document_collection('autotest_runs');

-- Billing and usage.
select workshop.create_document_collection('subscriptions');
select workshop.create_document_collection('invoices');
select workshop.create_document_collection('usage_events');

-- Compliance.
select workshop.create_document_collection('audit_log_entries');
select workshop.create_document_collection('dpa_acceptances');

-- Background work.
select workshop.create_document_collection('queued_jobs');

-- Lookup indexes on document fields. Every field below is written by
-- Pydantic with a fixed JSON type (text ids, integer timestamps), so the
-- expressions never fail on insert.

-- Sign-in by phone number (E.164) or e-mail; session by token hash.
create index if not exists users_phone_number_idx
    on workshop.users ((document ->> 'phone_number'));
create index if not exists users_email_idx
    on workshop.users ((document ->> 'email'));
create index if not exists user_sessions_token_hash_idx
    on workshop.user_sessions ((document ->> 'token_hash'));

-- Webhook routing: the business of an incoming message from its channel.
create index if not exists channels_kind_external_id_idx
    on workshop.channels ((document ->> 'kind'), (document ->> 'external_id'));

-- Customers by phone number and by channel identity.
create index if not exists contacts_phone_number_idx
    on workshop.contacts (business_id, (document ->> 'phone_number'));
create index if not exists contacts_channel_identities_idx
    on workshop.contacts using gin ((document -> 'channel_identities') jsonb_path_ops);

-- Conversation history.
create index if not exists conversations_contact_idx
    on workshop.conversations (business_id, (document ->> 'contact_id'));
create index if not exists messages_conversation_idx
    on workshop.messages (business_id, (document ->> 'conversation_id'));
create index if not exists llm_turns_conversation_idx
    on workshop.llm_turns (
        (document ->> 'conversation_id'),
        ((document ->> 'sequence_number')::bigint)
    );
create index if not exists calls_provider_call_id_idx
    on workshop.calls ((document ->> 'provider_call_id'));

-- Free slots and reminders: bookings by start time (UTC UNIX seconds).
create index if not exists bookings_starts_at_idx
    on workshop.bookings (business_id, ((document ->> 'starts_at')::bigint));
create index if not exists bookings_resource_starts_at_idx
    on workshop.bookings (
        business_id,
        (document ->> 'resource_id'),
        ((document ->> 'starts_at')::bigint)
    );

-- Usage per billing period.
create index if not exists usage_events_occurred_at_idx
    on workshop.usage_events (business_id, ((document ->> 'occurred_at')::bigint));

-- Due background jobs.
create index if not exists queued_jobs_due_idx
    on workshop.queued_jobs ((document ->> 'status'), ((document ->> 'run_at')::bigint));
