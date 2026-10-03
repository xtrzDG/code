-- 1044_guided_launch
--
-- The guided launch of an assistant: each business's activation
-- milestones (first test chat, going live, the first real conversation,
-- booking and handoff), the optional setup steps it skipped, and its
-- current "Apply changes" (the version being built, checked and
-- published). Each is a tenant collection with row-level security. The
-- documents of a business are found by their derived ids (one per
-- business and milestone kind, one setup state and one apply per
-- business) or by business_id, which every collection table indexes, so
-- no lookup columns are needed.

select workshop.create_document_collection('activation_events');
select workshop.create_document_collection('setup_states');
select workshop.create_document_collection('assistant_applies');
