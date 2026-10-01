-- 0002_channel_and_calendar_collections
--
-- Collections of the channels slice (message receipts against webhook
-- redelivery, staff Telegram links) and of the operations slice (Google
-- Calendar connection, OAuth state, event per booking). Same table shape and
-- row-level security as every collection (see 0001).

select workshop.create_document_collection('channel_message_receipts');
select workshop.create_document_collection('manager_telegram_links');
select workshop.create_document_collection('calendar_connections');
select workshop.create_document_collection('calendar_authorization_states');
select workshop.create_document_collection('calendar_event_links');

-- The platform bot resolves "/start <code>" by the code hash; the OAuth
-- callback resolves the state by its hash.
create index if not exists manager_telegram_links_code_hash_idx
    on workshop.manager_telegram_links ((document ->> 'code_hash'));
create index if not exists calendar_authorization_states_state_hash_idx
    on workshop.calendar_authorization_states ((document ->> 'state_hash'));
create index if not exists calendar_event_links_booking_idx
    on workshop.calendar_event_links (business_id, (document ->> 'booking_id'));
