-- 1083_booking_values
--
-- What bookings are worth (R8 services): a booking of a service, a package
-- or a room type stores its value (`value_minor`, in `currency_code`), and
-- the dashboard and the value model sum it by the database: the bookings
-- made in a period, per status and currency, bucketed by local day and by
-- opening hours (after-hours value). The rows are found by
-- (business_id, doc_created_at), as the booking counts are; the covering
-- index below also carries every column the sums read, so that a vacuumed
-- table answers them by an index-only scan (and the new integer lookup is
-- indexed, as every lookup field is).
--
-- bookings gain the optional `service_item_id`, `buffer_minutes`,
-- `value_minor` and `currency_code` (schema version 2); knowledge_items
-- gain `buffer_minutes`, `performer_resource_ids` and `seasonal_rates`
-- and resources `serves_item_ids` and `room_type_item_id` (version 2
-- each): nested or per-document fields nobody queries by, so no column.
--
-- Plain generated columns, as in 1010 and 1042 (forced row-level security
-- uses an index only for leakproof conditions on plain columns). Adding a
-- stored generated column rewrites the bookings table once, as 1042 did.

alter table workshop.bookings
    add column if not exists doc_currency_code text
        generated always as (document ->> 'currency_code') stored,
    add column if not exists doc_value_minor bigint
        generated always as ((document ->> 'value_minor')::bigint) stored;
create index if not exists bookings_doc_created_at_value_idx
    on workshop.bookings (business_id, doc_created_at)
    include (
        doc_status, doc_currency_code, doc_value_minor, doc_is_sandbox,
        doc_conversation_id
    );
