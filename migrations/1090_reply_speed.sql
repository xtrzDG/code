-- 1090_reply_speed
--
-- Fast, resilient replies (R9): quick messages of one customer are
-- answered together, and every assistant reply records how long the
-- customer waited.
--
-- inbound_events: when a customer's message is processed, the worker looks
-- for the same customer's other unprocessed messages of the last moments
-- (to answer them in one turn): the business's events by creation time,
-- (business_id, doc_created_at). The existing doc_created_at index serves
-- the platform-wide retention purge only.
--
-- messages gain `channel`, `reply_latency_ms`, `llm_round_count` and
-- `is_fallback_model` (schema version 3, all optional). The admin's client
-- page groups the replies of the last 7 days per channel into latency
-- buckets in the database (p50 and p95, the SLOW_REPLIES health issue):
-- assistant messages of a business by creation time, covered by the index
-- below, so a vacuumed table answers by an index-only scan (and the new
-- integer lookup is indexed, as every lookup field is).
--
-- Plain generated columns, as in 1010 and 1042 (forced row-level security
-- uses an index only for leakproof conditions on plain columns). Adding a
-- stored generated column rewrites the messages table once, as 1042 did;
-- run it in a quiet hour on a large installation.

create index if not exists inbound_events_doc_business_created_at_idx
    on workshop.inbound_events (business_id, doc_created_at);

alter table workshop.messages
    add column if not exists doc_channel text
        generated always as (document ->> 'channel') stored,
    add column if not exists doc_reply_latency_ms bigint
        generated always as ((document ->> 'reply_latency_ms')::bigint) stored;
create index if not exists messages_doc_reply_latency_idx
    on workshop.messages (business_id, doc_author, doc_created_at)
    include (doc_channel, doc_reply_latency_ms);
