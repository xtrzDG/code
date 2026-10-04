-- 1112_teach_from_conversations
--
-- Teaching the assistant from real conversations: "Fix this answer", the
-- reasons of a bad rating and the owner's own checks.
--
-- autotest_cases (business collection): the owner's checks ("My checks"),
--   a question and what the answer must do. Every autotest run of the
--   business plays its active checks; a business keeps a few dozen of
--   them, read whole by business_id (no lookup column).
--
-- conversations gain, in schema version 4, the review of a bad rating
--   (`rating_reason`, `rated_message_id`, `improved_at`) and, derived on
--   every review write, `awaits_improvement`: rated bad, not sandbox, and
--   nobody corrected the answer or saved a check from it since. The
--   Overview's "Answers worth improving" pages them by the latest message:
--     (business_id, doc_awaits_improvement, doc_last_message_at)
--
-- knowledge_items gain, in schema version 3, `correction_of`: the
--   assistant answer an owner corrected with the item, so correcting the
--   same answer again updates that item instead of adding another:
--     (business_id, doc_correction_of)
--
-- Plain generated columns, as in 1010, 1042 and 1053 (forced row-level
-- security uses an index only for leakproof conditions on plain columns).
-- Adding the stored columns rewrites conversations and knowledge_items
-- once; no backfill is needed, since no stored row has the new fields.

select workshop.create_document_collection('autotest_cases');

alter table workshop.conversations
    add column if not exists doc_awaits_improvement text
        generated always as (document ->> 'awaits_improvement') stored;
create index if not exists conversations_doc_awaits_improvement_idx
    on workshop.conversations
    (business_id, doc_awaits_improvement, doc_last_message_at);

alter table workshop.knowledge_items
    add column if not exists doc_correction_of text
        generated always as (document ->> 'correction_of') stored;
create index if not exists knowledge_items_doc_correction_of_idx
    on workshop.knowledge_items (business_id, doc_correction_of);
