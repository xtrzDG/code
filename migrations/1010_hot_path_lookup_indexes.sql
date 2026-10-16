-- 1010_hot_path_lookup_indexes
--
-- Indexed hot paths: the session of every signed-in request, the contact,
-- open conversation, hourly message count and transcript of every customer
-- message, sign-in by phone or e-mail, webhook routing, usage per billing
-- period, login-code throttling, and the purge of stale rows. The lookup
-- fields are declared in app/utilities/storage/document_lookup_fields.py;
-- a test checks that every declared field has its column or trigger here.
--
-- Why generated columns instead of the expression indexes of 0001. Every
-- collection table has FORCED row-level security. Postgres checks the RLS
-- policy before any condition that is not leakproof, and only leakproof
-- conditions may become index conditions. `document ->> 'token_hash' = $1`
-- calls the JSON operator, which is not leakproof, so those indexes were
-- never used: EXPLAIN showed a sequential scan of the whole table. A stored
-- generated column `doc_<field>` makes the field a plain column, and
-- `doc_token_hash = $1` is a leakproof comparison that uses a btree index.
-- Postgres computes the columns on every write (the application writes
-- only `document`). GIN containment (@>) is not leakproof either, so list
-- fields (`members[].user_id`) get one row per value in
-- workshop.document_lookup_keys, kept by a trigger.
--
-- Adding a stored column rewrites the table under an exclusive lock; at
-- today's table sizes that takes seconds. If migrations run as another role
-- than the application, grant the application role select, insert, update,
-- delete on workshop.document_lookup_keys (the trigger runs as the writer).

-- The backfill of the lookup keys reads every row (this transaction only).
select set_config('app.bypass_rls', 'on', true);

-- Sign-in: users by phone (E.164) or e-mail; sessions by token hash (every
-- signed-in request) and by expiry (purge); login codes by creation time
-- (throttling and purge).
alter table workshop.users
    add column if not exists doc_phone_number text
        generated always as (document ->> 'phone_number') stored,
    add column if not exists doc_email text
        generated always as (document ->> 'email') stored;
create index if not exists users_doc_phone_number_idx
    on workshop.users (doc_phone_number);
create index if not exists users_doc_email_idx
    on workshop.users (doc_email);

alter table workshop.user_sessions
    add column if not exists doc_token_hash text
        generated always as (document ->> 'token_hash') stored,
    add column if not exists doc_expires_at bigint
        generated always as ((document ->> 'expires_at')::bigint) stored;
create index if not exists user_sessions_doc_token_hash_idx
    on workshop.user_sessions (doc_token_hash);
create index if not exists user_sessions_doc_expires_at_idx
    on workshop.user_sessions (doc_expires_at);

alter table workshop.otp_challenges
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists otp_challenges_doc_created_at_idx
    on workshop.otp_challenges (doc_created_at);

-- Webhook routing: the channel of an incoming message.
alter table workshop.channels
    add column if not exists doc_kind text
        generated always as (document ->> 'kind') stored,
    add column if not exists doc_external_id text
        generated always as (document ->> 'external_id') stored;
create index if not exists channels_doc_kind_external_id_idx
    on workshop.channels (doc_kind, doc_external_id);

-- Customers by phone (typed or proved by the channel).
alter table workshop.contacts
    add column if not exists doc_phone_number text
        generated always as (document ->> 'phone_number') stored,
    add column if not exists doc_verified_phone_number text
        generated always as (document ->> 'verified_phone_number') stored;
create index if not exists contacts_doc_phone_number_idx
    on workshop.contacts (business_id, doc_phone_number);
create index if not exists contacts_doc_verified_phone_number_idx
    on workshop.contacts (business_id, doc_verified_phone_number);

-- Conversations of a contact (the open one, the hourly count), of a widget
-- visitor, and of a business newest first.
alter table workshop.conversations
    add column if not exists doc_contact_id text
        generated always as (document ->> 'contact_id') stored,
    add column if not exists doc_channel_user_id text
        generated always as (document ->> 'channel_user_id') stored,
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored,
    add column if not exists doc_last_message_at bigint
        generated always as ((document ->> 'last_message_at')::bigint) stored;
create index if not exists conversations_doc_contact_idx
    on workshop.conversations (business_id, doc_contact_id, doc_last_message_at);
create index if not exists conversations_doc_channel_user_idx
    on workshop.conversations (business_id, doc_channel_user_id);
create index if not exists conversations_doc_last_message_at_idx
    on workshop.conversations (business_id, doc_last_message_at);

-- Messages of a conversation in time order (transcript, hourly count).
alter table workshop.messages
    add column if not exists doc_conversation_id text
        generated always as (document ->> 'conversation_id') stored,
    add column if not exists doc_direction text
        generated always as (document ->> 'direction') stored,
    add column if not exists doc_author text
        generated always as (document ->> 'author') stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists messages_doc_conversation_idx
    on workshop.messages (business_id, doc_conversation_id, doc_created_at);

-- Model turns of a conversation in sequence (platform collection).
alter table workshop.llm_turns
    add column if not exists doc_conversation_id text
        generated always as (document ->> 'conversation_id') stored,
    add column if not exists doc_sequence_number bigint
        generated always as ((document ->> 'sequence_number')::bigint) stored;
create index if not exists llm_turns_doc_conversation_idx
    on workshop.llm_turns (doc_conversation_id, doc_sequence_number);

-- Calls by the voice platform's call id.
alter table workshop.calls
    add column if not exists doc_provider_call_id text
        generated always as (document ->> 'provider_call_id') stored;
create index if not exists calls_doc_provider_call_id_idx
    on workshop.calls (business_id, doc_provider_call_id);

-- Usage events of a billing period.
alter table workshop.usage_events
    add column if not exists doc_occurred_at bigint
        generated always as ((document ->> 'occurred_at')::bigint) stored;
create index if not exists usage_events_doc_occurred_at_idx
    on workshop.usage_events (business_id, doc_occurred_at);

-- Webhook redelivery receipts: one per business, channel and provider
-- message (inserted with "on conflict do nothing", so two instances never
-- both answer one message), purged after 30 days.
alter table workshop.channel_message_receipts
    add column if not exists doc_channel text
        generated always as (document ->> 'channel') stored,
    add column if not exists doc_provider_message_id text
        generated always as (document ->> 'provider_message_id') stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create unique index if not exists channel_message_receipts_doc_message_idx
    on workshop.channel_message_receipts
        (business_id, doc_channel, doc_provider_message_id);
create index if not exists channel_message_receipts_doc_created_at_idx
    on workshop.channel_message_receipts (doc_created_at);

-- "/start <code>" of the platform bot.
alter table workshop.manager_telegram_links
    add column if not exists doc_code_hash text
        generated always as (document ->> 'code_hash') stored;
create index if not exists manager_telegram_links_doc_code_hash_idx
    on workshop.manager_telegram_links (doc_code_hash);

-- The expression indexes these replace (never used under RLS, see above).
drop index if exists workshop.users_phone_number_idx;
drop index if exists workshop.users_email_idx;
drop index if exists workshop.user_sessions_token_hash_idx;
drop index if exists workshop.channels_kind_external_id_idx;
drop index if exists workshop.contacts_phone_number_idx;
drop index if exists workshop.contacts_channel_identities_idx;
drop index if exists workshop.conversations_contact_idx;
drop index if exists workshop.conversations_channel_user_idx;
drop index if exists workshop.messages_conversation_idx;
drop index if exists workshop.llm_turns_conversation_idx;
drop index if exists workshop.calls_provider_call_id_idx;
drop index if exists workshop.usage_events_occurred_at_idx;
drop index if exists workshop.manager_telegram_links_code_hash_idx;

-- Values of list fields: one row per (collection, field, value, document).
-- Same row-level security as the collections; business_id is the owning
-- row's.
create table if not exists workshop.document_lookup_keys (
    collection_name text not null,
    field_path text not null,
    field_value text not null,
    document_key text not null,
    business_id text,
    primary key (collection_name, field_path, field_value, document_key)
);
create index if not exists document_lookup_keys_document_idx
    on workshop.document_lookup_keys (collection_name, document_key);
alter table workshop.document_lookup_keys enable row level security;
alter table workshop.document_lookup_keys force row level security;
drop policy if exists business_isolation on workshop.document_lookup_keys;
create policy business_isolation on workshop.document_lookup_keys
    using (
        business_id = current_setting('app.business_id', true)
        or current_setting('app.bypass_rls', true) = 'on'
    )
    with check (
        business_id = current_setting('app.business_id', true)
        or current_setting('app.bypass_rls', true) = 'on'
    );

-- Keeps the lookup keys of one list field of a collection: arguments are
-- the list field and the field of its objects (members, user_id).
create or replace function workshop.sync_document_lookup_keys()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
declare
    list_field text := tg_argv[0];
    element_field text := tg_argv[1];
    lookup_path text := tg_argv[0] || '[].' || tg_argv[1];
begin
    if tg_op = 'UPDATE'
        and old.document -> list_field is not distinct from new.document -> list_field
        and old.business_id is not distinct from new.business_id then
        return null;
    end if;

    if tg_op in ('UPDATE', 'DELETE') then
        delete from workshop.document_lookup_keys as lookup_key
        where lookup_key.collection_name = tg_table_name::text
            and lookup_key.document_key = old.document_key
            and lookup_key.field_path = lookup_path;
    end if;

    if tg_op in ('INSERT', 'UPDATE') then
        insert into workshop.document_lookup_keys
            (collection_name, field_path, field_value, document_key, business_id)
        select distinct
            tg_table_name::text,
            lookup_path,
            list_element ->> element_field,
            new.document_key,
            new.business_id
        from jsonb_array_elements(
            case
                when jsonb_typeof(new.document -> list_field) = 'array'
                    then new.document -> list_field
                else '[]'::jsonb
            end
        ) as list_element
        where list_element ->> element_field is not null
        on conflict do nothing;
    end if;

    return null;
end;
$function$;

comment on function workshop.sync_document_lookup_keys() is
    'Keep workshop.document_lookup_keys in step with one list field of a collection.';

drop trigger if exists businesses_members_lookup_keys on workshop.businesses;
create trigger businesses_members_lookup_keys
    after insert or update or delete on workshop.businesses
    for each row execute function workshop.sync_document_lookup_keys('members', 'user_id');

drop trigger if exists contacts_channel_identities_lookup_keys on workshop.contacts;
create trigger contacts_channel_identities_lookup_keys
    after insert or update or delete on workshop.contacts
    for each row execute function
        workshop.sync_document_lookup_keys('channel_identities', 'channel_user_id');

-- Keys of the rows written before this migration.
insert into workshop.document_lookup_keys
    (collection_name, field_path, field_value, document_key, business_id)
select distinct
    'businesses',
    'members[].user_id',
    member ->> 'user_id',
    business.document_key,
    business.business_id
from workshop.businesses as business
cross join lateral jsonb_array_elements(
    case
        when jsonb_typeof(business.document -> 'members') = 'array'
            then business.document -> 'members'
        else '[]'::jsonb
    end
) as member
where member ->> 'user_id' is not null
on conflict do nothing;

insert into workshop.document_lookup_keys
    (collection_name, field_path, field_value, document_key, business_id)
select distinct
    'contacts',
    'channel_identities[].channel_user_id',
    channel_identity ->> 'channel_user_id',
    contact.document_key,
    contact.business_id
from workshop.contacts as contact
cross join lateral jsonb_array_elements(
    case
        when jsonb_typeof(contact.document -> 'channel_identities') = 'array'
            then contact.document -> 'channel_identities'
        else '[]'::jsonb
    end
) as channel_identity
where channel_identity ->> 'channel_user_id' is not null
on conflict do nothing;
