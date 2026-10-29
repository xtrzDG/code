-- 0004_widget_lookup_indexes
--
-- The website widget polls for answers of its visitor: their conversations
-- are found by the widget's session key (the conversation's channel user)
-- instead of reading every conversation of the business. Messages of a
-- conversation already have messages_conversation_idx (see 0001).

create index if not exists conversations_channel_user_idx
    on workshop.conversations (business_id, (document ->> 'channel_user_id'));
