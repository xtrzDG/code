-- 1195_widget_poll_read
--
-- A website-widget poll's reads in one statement whose plan the database
-- keeps.
--
-- Every open chat polls every 4 s. A poll read the business's widget
-- limits, the visitor's conversations, where its newest messages stand and
-- the messages after its cursor: up to four statements in two
-- transactions, eight round trips with its rate-limit count
-- (docs/operations/capacity.md, "The runs of 2026-10-19 and 2026-10-20").
-- workshop.read_widget_poll(...) returns all of it in one statement. It is a
-- PL/pgSQL function because the application sends no prepared statements
-- (transaction poolers do not keep them): the function's query plan is
-- cached per session instead of planned for every poll.
--
-- Each part reads by the index the repositories use:
--
-- - business_limits by its key (the derived id of the business);
-- - conversations by (business_id, doc_channel_user_id), numbered in the
--   repositories' order (last message first, ties in first-write order);
-- - per shown conversation (web chat, not sandbox) its newest window_size
--   messages backwards on (business_id, doc_conversation_id,
--   doc_created_at), then the newest window_size of them all;
-- - the documents of only those that come after the cursor in answer
--   order (created_at, then id in code-point order), so a poll that finds
--   nothing new reads no message document.
--
-- Rows carry their kind: 'origins' (the limits document), 'conversation'
-- (place, key, whether shown, document) and 'message' (created_at, key,
-- the document when after the cursor). The function is SECURITY INVOKER
-- and sets no scope: row-level security binds it in the caller's scope,
-- and every table is filtered by the business asked for as well. A new
-- function only: nothing existing is rewritten or locked, and the previous
-- release never calls it.

create or replace function workshop.read_widget_poll(
    poll_business_id text,
    poll_visitor text,
    shown_channel text,
    limits_key text,
    window_size integer,
    after_key text
) returns table (
    kind text,
    poll_position bigint,
    row_key text,
    is_shown boolean,
    row_document text
)
language plpgsql
stable
as $function$
begin
    return query
    with visitor_conversations as (
        select
            conversation.document_key,
            conversation.document,
            row_number() over (
                order by conversation.doc_last_message_at desc,
                    conversation.created_at, conversation.row_sequence
            ) as place,
            conversation.doc_channel = shown_channel
                and coalesce(conversation.doc_is_sandbox, 'false') <> 'true'
                as shown
        from workshop.conversations as conversation
        where conversation.business_id = poll_business_id
            and conversation.doc_channel_user_id = poll_visitor
    ),
    newest_messages as (
        select message.doc_created_at, message.document_key, message.document
        from visitor_conversations as visitor_conversation
        cross join lateral (
            select candidate.doc_created_at, candidate.document_key,
                candidate.created_at, candidate.row_sequence,
                candidate.document
            from workshop.messages as candidate
            where candidate.business_id = poll_business_id
                and candidate.doc_conversation_id
                    = visitor_conversation.document_key
            order by candidate.doc_created_at desc, candidate.created_at desc,
                candidate.row_sequence desc
            limit window_size
        ) as message
        where visitor_conversation.shown
        order by message.doc_created_at desc, message.created_at desc,
            message.row_sequence desc
        limit window_size
    )
    select 'origins'::text, null::bigint, null::text, null::boolean,
        limits.document::text
    from workshop.business_limits as limits
    where limits.business_id = poll_business_id
        and limits.document_key = limits_key
    union all
    select 'conversation'::text, visitor_conversations.place,
        visitor_conversations.document_key, visitor_conversations.shown,
        visitor_conversations.document::text
    from visitor_conversations
    union all
    select 'message'::text, newest_messages.doc_created_at,
        newest_messages.document_key, null::boolean,
        case
            when (newest_messages.doc_created_at,
                    newest_messages.document_key collate "C")
                > (
                    max(newest_messages.doc_created_at) filter (
                        where newest_messages.document_key = after_key
                    ) over (),
                    after_key collate "C"
                )
            then newest_messages.document::text
        end
    from newest_messages;
end;
$function$;

comment on function workshop.read_widget_poll(
    text, text, text, text, integer, text
) is
    'A website-widget poll''s reads in one statement: the business''s '
    'widget limits, the visitor''s conversations, its newest message '
    'positions and the messages after the cursor (migration 1195).';
