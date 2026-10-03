-- 1052_hosted_chat_addresses
--
-- The hosted chat page of a business (/c/{slug} on the cabinet's site):
-- public_slug_claims keeps every address a business took, keyed by the
-- slug itself, so the primary key makes an address unique across
-- businesses even between concurrent requests ("insert ... on conflict do
-- nothing" sees rows that row-level security hides). Claims are never
-- released: after a change of address, printed QR codes still lead to the
-- business and no other business can take the old address over.
--
-- A tenant collection with the usual row-level security: a business writes
-- only its own claims. A visitor's page reads one claim by its key before
-- the business is known, explicitly platform-wide. No lookup columns are
-- needed. The business's current address is the `public_slug` field of
-- its document.

select workshop.create_document_collection('public_slug_claims');
