-- 1042_list_pages_and_aggregates
--
-- Lists, the dashboard and the admin page stay fast with years of data.
-- The cabinet's lists are keyset pages (an index range scan that starts at
-- the cursor: page 1000 costs what page 1 costs), and the dashboard and the
-- admin client summaries are counted by the database (grouped counts and
-- sums, no document is read into the application). The lookup fields are
-- declared in app/utilities/storage/document_lookup_catalog.py; a test
-- checks that every declared field has its column, index or trigger here.
--
-- Plain generated columns, as in 1010: every table has forced row-level
-- security, and only leakproof conditions on plain columns become index
-- conditions. Flags (`is_sandbox`, `is_after_hours`, `is_resolved`) are the
-- JSON text 'true'/'false'; sandbox rows are left out with
-- "doc_is_sandbox is distinct from 'true'", which keeps a row written
-- before its flag existed.
--
-- Columns and indexes that migration 1040 (navigation badges) also creates
-- use the same names and "if not exists", so either order works.
--
-- Adding stored columns rewrites the tables under an exclusive lock; at
-- today's table sizes that takes seconds (docs/operations/capacity.md says
-- how to run it on large tables). If migrations run as another role than
-- the application, the trigger below needs the grants of 1010.

-- The backfill of the lookup keys reads every message (this transaction only).
select set_config('app.bypass_rls', 'on', true);

-- Conversations: the feed's filters (channel, sandbox) on the
-- (business_id, doc_last_message_at) pages of 1010, and the dashboard's
-- counts of what started in a period by channel, language and opening hours.
alter table workshop.conversations
    add column if not exists doc_channel text
        generated always as (document ->> 'channel') stored,
    add column if not exists doc_language text
        generated always as (document ->> 'language') stored,
    add column if not exists doc_is_after_hours text
        generated always as (document ->> 'is_after_hours') stored,
    add column if not exists doc_is_sandbox text
        generated always as (document ->> 'is_sandbox') stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists conversations_doc_created_at_idx
    on workshop.conversations (business_id, doc_created_at);

-- Messages: customer messages of a period (dashboard), the model usage of
-- a conversation (its card) and per conversation of a billing window
-- (admin; covered, so the sums read only the index), and messages with a
-- failed tool call (admin health).
alter table workshop.messages
    add column if not exists doc_input_tokens bigint
        generated always as ((document ->> 'input_tokens')::bigint) stored,
    add column if not exists doc_output_tokens bigint
        generated always as ((document ->> 'output_tokens')::bigint) stored,
    add column if not exists doc_cost_micro_usd bigint
        generated always as ((document ->> 'cost_micro_usd')::bigint) stored;
create index if not exists messages_doc_author_created_at_idx
    on workshop.messages (business_id, doc_author, doc_created_at);
create index if not exists messages_doc_created_at_idx
    on workshop.messages (business_id, doc_created_at)
    include (
        doc_conversation_id, doc_input_tokens, doc_output_tokens, doc_cost_micro_usd
    );

drop trigger if exists messages_tool_calls_lookup_keys on workshop.messages;
create trigger messages_tool_calls_lookup_keys
    after insert or update or delete on workshop.messages
    for each row execute function
        workshop.sync_document_lookup_keys('tool_calls', 'is_error');

insert into workshop.document_lookup_keys
    (collection_name, field_path, field_value, document_key, business_id)
select distinct
    'messages',
    'tool_calls[].is_error',
    tool_call ->> 'is_error',
    message.document_key,
    message.business_id
from workshop.messages as message
cross join lateral jsonb_array_elements(
    case
        when jsonb_typeof(message.document -> 'tool_calls') = 'array'
            then message.document -> 'tool_calls'
        else '[]'::jsonb
    end
) as tool_call
where tool_call ->> 'is_error' is not null
on conflict do nothing;

-- Calls of one conversation (the conversation card).
alter table workshop.calls
    add column if not exists doc_conversation_id text
        generated always as (document ->> 'conversation_id') stored;
create index if not exists calls_doc_conversation_idx
    on workshop.calls (business_id, doc_conversation_id);

-- Bookings: pages by start time, the ones not over yet (availability),
-- created in a period (dashboard), of one conversation, and by status
-- (navigation badges, as in 1040).
alter table workshop.bookings
    add column if not exists doc_conversation_id text
        generated always as (document ->> 'conversation_id') stored,
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored,
    add column if not exists doc_resource_id text
        generated always as (document ->> 'resource_id') stored,
    add column if not exists doc_is_sandbox text
        generated always as (document ->> 'is_sandbox') stored,
    add column if not exists doc_starts_at bigint
        generated always as ((document ->> 'starts_at')::bigint) stored,
    add column if not exists doc_ends_at bigint
        generated always as ((document ->> 'ends_at')::bigint) stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists bookings_doc_status_starts_at_idx
    on workshop.bookings (business_id, doc_status, doc_starts_at);
create index if not exists bookings_doc_starts_at_idx
    on workshop.bookings (business_id, doc_starts_at);
create index if not exists bookings_doc_ends_at_idx
    on workshop.bookings (business_id, doc_ends_at);
create index if not exists bookings_doc_created_at_idx
    on workshop.bookings (business_id, doc_created_at);
create index if not exists bookings_doc_conversation_idx
    on workshop.bookings (business_id, doc_conversation_id);

-- Leads: pages newest first, counts per status, of one conversation.
alter table workshop.leads
    add column if not exists doc_conversation_id text
        generated always as (document ->> 'conversation_id') stored,
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored,
    add column if not exists doc_is_sandbox text
        generated always as (document ->> 'is_sandbox') stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists leads_doc_status_idx
    on workshop.leads (business_id, doc_status);
create index if not exists leads_doc_created_at_idx
    on workshop.leads (business_id, doc_created_at);
create index if not exists leads_doc_conversation_idx
    on workshop.leads (business_id, doc_conversation_id);

-- Handoffs: open ones by urgency and age (the work queue), resolved ones
-- by resolution time, counts per status, created in a period (dashboard,
-- admin), of one conversation.
alter table workshop.handoffs
    add column if not exists doc_conversation_id text
        generated always as (document ->> 'conversation_id') stored,
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored,
    add column if not exists doc_urgency text
        generated always as (document ->> 'urgency') stored,
    add column if not exists doc_reason text
        generated always as (document ->> 'reason') stored,
    add column if not exists doc_is_sandbox text
        generated always as (document ->> 'is_sandbox') stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored,
    add column if not exists doc_resolved_at bigint
        generated always as ((document ->> 'resolved_at')::bigint) stored;
create index if not exists handoffs_doc_status_idx
    on workshop.handoffs (business_id, doc_status);
create index if not exists handoffs_doc_queue_idx
    on workshop.handoffs (business_id, doc_status, doc_urgency, doc_created_at);
create index if not exists handoffs_doc_resolved_at_idx
    on workshop.handoffs (business_id, doc_resolved_at);
create index if not exists handoffs_doc_created_at_idx
    on workshop.handoffs (business_id, doc_created_at);
create index if not exists handoffs_doc_conversation_idx
    on workshop.handoffs (business_id, doc_conversation_id);

-- Unanswered questions: open ones most asked first (the default list), all
-- of them in that order, and the open count.
alter table workshop.unanswered_questions
    add column if not exists doc_is_resolved text
        generated always as (document ->> 'is_resolved') stored,
    add column if not exists doc_is_sandbox text
        generated always as (document ->> 'is_sandbox') stored,
    add column if not exists doc_occurrence_count bigint
        generated always as ((document ->> 'occurrence_count')::bigint) stored,
    add column if not exists doc_last_seen_at bigint
        generated always as ((document ->> 'last_seen_at')::bigint) stored;
create index if not exists unanswered_questions_doc_open_rank_idx
    on workshop.unanswered_questions
        (business_id, doc_is_resolved, doc_occurrence_count, doc_last_seen_at);
create index if not exists unanswered_questions_doc_rank_idx
    on workshop.unanswered_questions
        (business_id, doc_occurrence_count, doc_last_seen_at);

-- The audit log newest first, of one person, filtered by operation and
-- entity type; the entity types and persons of the filters are grouped.
alter table workshop.audit_log_entries
    add column if not exists doc_actor_id text
        generated always as (document ->> 'actor_id') stored,
    add column if not exists doc_action text
        generated always as (document ->> 'action') stored,
    add column if not exists doc_entity text
        generated always as (document ->> 'entity') stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists audit_log_entries_doc_created_at_idx
    on workshop.audit_log_entries (business_id, doc_created_at);
create index if not exists audit_log_entries_doc_actor_idx
    on workshop.audit_log_entries (business_id, doc_actor_id, doc_created_at);

-- Channels in error (navigation badges, as in 1040).
alter table workshop.channels
    add column if not exists doc_status text
        generated always as (document ->> 'status') stored;
create index if not exists channels_doc_status_idx
    on workshop.channels (business_id, doc_status);
