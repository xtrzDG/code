-- 1100_customer_sources_and_topics
--
-- Where customers come from and what they ask about (W10 value proof).
--
-- conversations gain the optional `acquisition_source` (schema version 3):
--   the tag of the link, ad or number a customer came by, set when the
--   conversation starts. The Reports page counts the conversations that
--   started in a period per source and channel:
--     (business_id, doc_created_at) include (doc_acquisition_source, ...)
--   so the grouped count reads only the index (an index-only scan on a
--   vacuumed table), as the dashboard's counts of 1042 do.
-- conversation_topics: the topics of one business's recent conversations
--   (labels and counts, no customer text), one document per business (id
--   derived from it) that the nightly grouping replaces; read by id.
--
-- inbound_events (version 4: the customer message's `acquisition_source`),
-- digest_preferences (version 2: the channels digests go to) and
-- value_reports (version 3: the plan's cost and the return multiple) gain
-- nested or per-document fields nobody queries by, so no column.
--
-- A plain generated column, as in 1010 and 1042 (forced row-level security
-- uses an index only for leakproof conditions on plain columns). Adding a
-- stored generated column rewrites the conversations table once under an
-- exclusive lock; at today's sizes that takes seconds
-- (docs/operations/capacity.md says how to run it on large tables).

select workshop.create_document_collection('conversation_topics');

alter table workshop.conversations
    add column if not exists doc_acquisition_source text
        generated always as (document ->> 'acquisition_source') stored;
create index if not exists conversations_doc_created_at_source_idx
    on workshop.conversations (business_id, doc_created_at)
    include (doc_acquisition_source, doc_channel, doc_is_sandbox);
