-- 1053_team_inbox
--
-- The team inbox: several people share a business's conversations safely.
--
-- conversations: who is assigned (`assignee_user_id`, changed only by a
--   compare-and-set on `assignment_revision`), whether a request of the
--   conversation is new or in progress (`has_open_request`) and whether it
--   waits for the team (`awaits_team`: a person is needed or a request is
--   open). The inbox views page these by `last_message_at` (keyset pages,
--   1042) and count them by group:
--     needs a person  (business_id, doc_status, doc_last_message_at)
--     requests        (business_id, doc_has_open_request, doc_last_message_at)
--     mine/unassigned (business_id, doc_awaits_team, doc_assignee_user_id,
--                      doc_last_message_at); "unassigned" is
--                      doc_assignee_user_id is null, which a btree serves.
-- conversation_notes: internal notes of the team, read per conversation
--   newest first; never part of the messages, so never sent to the
--   customer or the language model.
-- quick_reply_libraries: the saved replies of a business, one document per
--   business (id derived from it), read by id.
-- inbox_settings: auto-assignment of new handoffs and requests, one
--   document per business (id derived from it), read by id.
--
-- Plain generated columns, as in 1010 and 1042 (forced row-level security
-- uses an index only for leakproof conditions on plain columns). Adding the
-- columns rewrites the conversations table under an exclusive lock; at
-- today's sizes that takes seconds (docs/operations/capacity.md).
--
-- The backfill marks the conversations that already have an open request
-- or a handoff, so the views are right from the first deploy. It reads
-- every business, so it bypasses row-level security in this transaction
-- only.

select set_config('app.bypass_rls', 'on', true);

alter table workshop.conversations
    add column if not exists doc_assignee_user_id text
        generated always as (document ->> 'assignee_user_id') stored,
    add column if not exists doc_has_open_request text
        generated always as (document ->> 'has_open_request') stored,
    add column if not exists doc_awaits_team text
        generated always as (document ->> 'awaits_team') stored;
create index if not exists conversations_doc_status_last_message_at_idx
    on workshop.conversations (business_id, doc_status, doc_last_message_at);
create index if not exists conversations_doc_open_request_idx
    on workshop.conversations
    (business_id, doc_has_open_request, doc_last_message_at);
create index if not exists conversations_doc_awaits_team_idx
    on workshop.conversations
    (business_id, doc_awaits_team, doc_assignee_user_id, doc_last_message_at);

update workshop.conversations as conversation
set document = conversation.document || '{"has_open_request": true}'::jsonb
where exists (
    select 1
    from workshop.leads as lead
    where lead.business_id = conversation.business_id
        and lead.doc_conversation_id = conversation.document_key
        and lead.doc_status in ('new', 'in_progress')
);
update workshop.conversations
set document = document || '{"awaits_team": true}'::jsonb
where doc_status = 'handoff' or doc_has_open_request = 'true';

select workshop.create_document_collection('conversation_notes');
select workshop.create_document_collection('quick_reply_libraries');
select workshop.create_document_collection('inbox_settings');

alter table workshop.conversation_notes
    add column if not exists doc_conversation_id text
        generated always as (document ->> 'conversation_id') stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists conversation_notes_doc_conversation_idx
    on workshop.conversation_notes
    (business_id, doc_conversation_id, doc_created_at);
