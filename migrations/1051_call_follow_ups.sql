-- 1051_call_follow_ups
--
-- What follows a phone call: a short summary for staff after every call
-- (kept on the call row itself, no schema change), and a message to a
-- caller who did not get through (the text-back).
--
-- missed_calls: one call whose caller did not get through (no answer, busy,
--   hung up before the assistant, a failed start, a transfer nobody picked
--   up) and how the text-back went. The id derives from the business, the
--   reporting source and the provider's call id. Read by id (the worker
--   that sends it), newest first by business (Settings → Calls) and by
--   creation time for the 90-day retention purge.
-- call_settings: the call follow-up settings of one business (summaries,
--   text-backs, the WhatsApp template), id derived from the business.
--
-- Both belong to one business and get the usual row-level security.

select workshop.create_document_collection('missed_calls');
select workshop.create_document_collection('call_settings');

alter table workshop.missed_calls
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists missed_calls_doc_created_at_idx
    on workshop.missed_calls (business_id, doc_created_at);
