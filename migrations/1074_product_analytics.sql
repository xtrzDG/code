-- 1074_product_analytics
--
-- First-party growth analytics for the founder (no third-party tracker).
--
-- product_events: one step of an owner's way from sign-up to paying
--   (signed up, business created, tunnel steps, launch, agreement,
--   channel, milestones, trial, subscription, plan change, cancellation,
--   failed payment). A platform collection: a sign-in names no business,
--   and GET /v1/admin/metrics reads every business's steps. Read by name
--   within a time range (the funnel, the cohorts, the MRR movements):
--   (doc_name, doc_occurred_at).
-- web_vital_samples: Core Web Vitals the cabinet's pages report (LCP, INP,
--   CLS per route template and device class), purged after 90 days. The
--   metrics count them per vital within a time range, grouped by route
--   and device and bucketed by value, from the index alone:
--   (doc_metric, doc_created_at) including route, device and value; the
--   purge deletes by (doc_created_at).
--
-- users gain the optional `signup_attribution` (schema version 2): a
-- nested field nobody queries by, so no column.
--
-- Plain generated columns, as in 1010 and 1042 (forced row-level security
-- uses an index only for leakproof conditions on plain columns).

select workshop.create_document_collection('product_events');
select workshop.create_document_collection('web_vital_samples');

alter table workshop.product_events
    add column if not exists doc_name text
        generated always as (document ->> 'name') stored,
    add column if not exists doc_occurred_at bigint
        generated always as ((document ->> 'occurred_at')::bigint) stored;
create index if not exists product_events_doc_name_occurred_at_idx
    on workshop.product_events (doc_name, doc_occurred_at);

alter table workshop.web_vital_samples
    add column if not exists doc_metric text
        generated always as (document ->> 'metric') stored,
    add column if not exists doc_route text
        generated always as (document ->> 'route') stored,
    add column if not exists doc_device_class text
        generated always as (document ->> 'device_class') stored,
    add column if not exists doc_value bigint
        generated always as ((document ->> 'value')::bigint) stored,
    add column if not exists doc_created_at bigint
        generated always as ((document ->> 'created_at')::bigint) stored;
create index if not exists web_vital_samples_doc_metric_created_at_idx
    on workshop.web_vital_samples (doc_metric, doc_created_at)
    include (doc_route, doc_device_class, doc_value);
create index if not exists web_vital_samples_doc_created_at_idx
    on workshop.web_vital_samples (doc_created_at);
