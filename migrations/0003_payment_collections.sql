-- 0003_payment_collections
--
-- Collections of the billing slice: Flitt checkout orders (looked up by
-- their id from the verified payment webhook) and the 80 % package usage
-- warnings (one per business, period and metric). Same table shape and
-- row-level security as every collection (see 0001).

select workshop.create_document_collection('payment_orders');
select workshop.create_document_collection('package_usage_warnings');
