-- 1043_staff_notifications
--
-- Staff notifications that arrive: besides the Telegram bot and the
-- WhatsApp template, e-mail, SMS and Web Push on the devices of cabinet
-- users, each going through the outbox (outbound_messages, 1020).
--
-- push_subscriptions: one browser of a cabinet user that shows the
--   business's notifications (endpoint and keys of the Push API; the id
--   derives from business, user and endpoint). Read by business when an
--   alert goes out, by business and user in Settings.
-- notification_preferences: one user's events and quiet hours for the
--   notifications of one business on their devices (id from business and
--   user, read by id).
-- staff_delivery_states: how the latest notification to each staff contact
--   went (id from business and the contact's channel and address, which
--   are not stored), read by business in Settings.
--
-- All three belong to one business and get the usual row-level security.

select workshop.create_document_collection('push_subscriptions');
select workshop.create_document_collection('notification_preferences');
select workshop.create_document_collection('staff_delivery_states');

alter table workshop.push_subscriptions
    add column if not exists doc_user_id text
        generated always as (document ->> 'user_id') stored;
create index if not exists push_subscriptions_doc_user_id_idx
    on workshop.push_subscriptions (business_id, doc_user_id);
