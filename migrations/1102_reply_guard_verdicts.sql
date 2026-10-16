-- 1102_reply_guard_verdicts
--
-- Stored reply guard verdicts (R10): messages gain `guard_verdict`,
-- `guard_reasons`, `unverified_values` and `claim_findings` on the
-- assistant's replies and `injection_flag` on customer messages that look
-- like prompt injection (schema version 4, all optional).
--
-- Two readers, both served by existing indexes; the new values are plain
-- generated columns (filter fields, no index of their own):
--
-- * the admin's client page counts the last 7 days of a business's
--   messages by author, guard verdict and injection flag (GUARD_SPIKE):
--   `messages_doc_created_at_idx` (business_id, doc_created_at, 1042)
--   selects the period;
-- * every customer message counts the contact's flagged messages of the
--   last day, one conversation at a time: the transcript index
--   (business_id, doc_conversation_id, doc_created_at, 1010) selects the
--   rows and the flag narrows them.
--
-- Plain generated columns, as in 1010, 1042 and 1090 (forced row-level
-- security uses an index only for leakproof conditions on plain columns).
-- Adding a stored generated column rewrites the messages table once, as
-- 1090 did; run it in a quiet hour on a large installation.

alter table workshop.messages
    add column if not exists doc_guard_verdict text
        generated always as (document ->> 'guard_verdict') stored,
    add column if not exists doc_injection_flag text
        generated always as (document ->> 'injection_flag') stored;
