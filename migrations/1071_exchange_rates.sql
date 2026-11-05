-- 1071_exchange_rates
--
-- Exchange rates as dated data: every rate the daily refresh reads from the
-- National Bank of Georgia (about 40 currencies against the lari) and the
-- European Central Bank (euro reference rates), one row per source, pair
-- and day, plus the euro cross rates derived from them (marked derived).
-- The current rate of a pair is its newest row: one probe of the index on
-- (pair, day). Money conversions read them through ExchangeRateRegistry;
-- the static catalog is only the fallback.
--
-- A platform collection (rates belong to no business): row-level security
-- as on every collection, and its adapter always runs platform-wide.
-- A new, small table: the generated lookup columns cost no lock on data.

select workshop.create_document_collection('exchange_rates');

alter table workshop.exchange_rates
    add column if not exists doc_pair text
        generated always as (document ->> 'pair') stored;
alter table workshop.exchange_rates
    add column if not exists doc_rate_day bigint
        generated always as ((document ->> 'rate_day')::bigint) stored;
create index if not exists exchange_rates_doc_pair_rate_day_idx
    on workshop.exchange_rates (doc_pair, doc_rate_day);
