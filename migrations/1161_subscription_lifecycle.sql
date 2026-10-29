-- 1161_subscription_lifecycle
--
-- Cancel reasons, save offers, a seasonal pause and win-back messages
-- (R14-SUB-LIFECYCLE).
--
-- subscription_events (business collection): the steps of a subscription's
--   life: a cancellation with its reason and the owner's words, an offer
--   taken instead (pause, cheaper plan, one-time credit), a pause
--   scheduled, started and ended, a win-back message sent on day 14 and
--   day 30. A business's steps (the pause cap of four months in twelve)
--   read through the business index the table already has.
--     (kind, occurred_at)  the founder's churn metrics and the win-back
--                          job's cancellations, across businesses
--
-- subscriptions (version 4: pause_starts_at, pause_until) and
-- billing_credits (version 3: save_offer_for) gain optional fields nobody
-- queries by: no column, no index.
--
-- The table is new and empty, so its lookup columns (trigger-filled, as
-- every lookup column from 1122 on) and index are added right here.

select workshop.create_document_collection('subscription_events');

select workshop.add_lookup_column('subscription_events', 'kind', 'text');
select workshop.add_lookup_column('subscription_events', 'occurred_at', 'bigint');
create index if not exists subscription_events_doc_kind_occurred_at_idx
    on workshop.subscription_events (doc_kind, doc_occurred_at);
