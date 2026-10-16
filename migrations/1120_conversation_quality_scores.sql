-- 1120_conversation_quality_scores
--
-- Production quality: every night the judge model scores a small sample of
-- the day's real conversations (QUALITY_SAMPLE_PERCENT, at most
-- QUALITY_SAMPLE_PER_BUSINESS per business and QUALITY_SAMPLE_BUDGET_CENTS
-- of model cost in all).
--
-- conversation_quality_scores (business collection, new): one score per
--   sampled conversation (the id derives from the conversation): the five
--   criteria, their average in hundredths, the judge's notes and the cost.
--     (business_id, doc_judged_at)  a business's daily trend (admin client
--                                   page) and its lowest scores
--     (doc_judged_at)               across businesses: the night's
--                                   spending, the QUALITY_DROP alert and
--                                   the 90-day purge
--     (business_id, doc_score_hundredths)  a business's lowest scores
--     (business_id, doc_cost_micro_usd)    what judging a business cost
--   Scores and costs are also summed per day by the database (count_by
--   totals).
--
-- A new, empty table: its stored generated columns and plain indexes take
-- no lock anything waits on. Plain generated columns, as in 1010 and 1042
-- (forced row-level security uses an index only for leakproof conditions
-- on plain columns).

select workshop.create_document_collection('conversation_quality_scores');

alter table workshop.conversation_quality_scores
    add column if not exists doc_judged_at bigint
        generated always as ((document ->> 'judged_at')::bigint) stored,
    add column if not exists doc_score_hundredths bigint
        generated always as ((document ->> 'score_hundredths')::bigint) stored,
    add column if not exists doc_cost_micro_usd bigint
        generated always as ((document ->> 'cost_micro_usd')::bigint) stored;
create index if not exists conversation_quality_scores_doc_judged_at_idx
    on workshop.conversation_quality_scores (business_id, doc_judged_at);
create index if not exists conversation_quality_scores_judged_at_idx
    on workshop.conversation_quality_scores (doc_judged_at);
create index if not exists conversation_quality_scores_doc_score_hundredths_idx
    on workshop.conversation_quality_scores (business_id, doc_score_hundredths);
create index if not exists conversation_quality_scores_doc_cost_micro_usd_idx
    on workshop.conversation_quality_scores (business_id, doc_cost_micro_usd);
