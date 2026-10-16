-- 1080_activation_follow_up
--
-- After the launch the cabinet keeps guiding the owner to the first real
-- customer, and a periodic job brings stuck owners back.
--
-- nudges_sent: each activation nudge a business was sent (days 1, 3 and 7
--   without going live; days 2 and 5 after going live without a second
--   channel or a first conversation; day 10 without a printed QR code or a
--   hosted page visit). The id derives from the business and the nudge
--   code, so the primary key keeps it unique on (business_id, nudge_code)
--   and a nudge goes out once across restarts and workers.
-- onboarding_requests: a business's request for a done-for-you setup (the
--   DONE_FOR_YOU setup option, which carries the plan's setup fee); one
--   per business, its id derived from it.
--
-- Both are tenant collections with row-level security, read by their
-- derived ids or by business_id, which every collection table indexes, so
-- no lookup columns are needed. setup_states (version 2) and
-- subscriptions (version 2) gain optional fields nobody queries by.

select workshop.create_document_collection('nudges_sent');
select workshop.create_document_collection('onboarding_requests');
