-- 1142_spend_guard_and_widget_origins
--
-- workshop:no-transaction
--
-- The spend guard: a business's provider spend of its day against its
-- limits before each model turn and each call, the platform's spend for the
-- admin tile and the spend alerts, and the websites allowed to show a
-- business's chat. This file runs statement by statement outside a
-- transaction (the header above), so every statement is idempotent: a
-- failed try runs the file again from the top.
--
-- usage_events (existing, busy): three trigger-filled lookup columns (the
--   online-safe pattern of migrations/README.md: nullable, no default, no
--   rewrite), so the database sums spend by kind:
--     doc_kind, doc_cost_micro_usd, doc_quantity
--   A business's day is summed over its (business_id, doc_occurred_at)
--   index (1010); the platform's day over a new BRIN index on
--   doc_occurred_at, 32 pages a range (rows arrive in time order, so a day
--   is a few ranges; the index is a few pages, and no business's query
--   prefers it over 1010's btree), built CONCURRENTLY (no write waits).
--   It also summarizes the two summed columns: every integer lookup column
--   has an index, and a range summary costs a BRIN almost nothing.
--   Rows written before this release get their columns from
--   `workshop backfill-lookup --collection usage_events` after the deploy;
--   until then a sum leaves them out (docs/operations/deploys.md).
--
-- business_limits (business collection, new): one business's daily spend
--   ceilings and the websites allowed to show its chat. Read by id only
--   (the id derives from the business), so no lookup column.
--
-- spend_limit_marks (business collection, new): the days a business passed
--   its soft or hard spend limit, inserted once per business, day and
--   level (the id derives from them). Read by id on each turn;
--     (doc_day)  the marks of one day across businesses (the admin tile)
--   A new, empty table: its column and index cost nothing to add.

select workshop.create_document_collection('business_limits');
select workshop.create_document_collection('spend_limit_marks');
select workshop.add_lookup_column('spend_limit_marks', 'day', 'text');
create index concurrently if not exists spend_limit_marks_doc_day_idx
    on workshop.spend_limit_marks (doc_day);

select workshop.add_lookup_column('usage_events', 'kind', 'text');
select workshop.add_lookup_column('usage_events', 'cost_micro_usd', 'bigint');
select workshop.add_lookup_column('usage_events', 'quantity', 'bigint');
create index concurrently if not exists usage_events_doc_occurred_at_brin_idx
    on workshop.usage_events
    using brin (doc_occurred_at, doc_cost_micro_usd, doc_quantity)
    with (pages_per_range = 32);
