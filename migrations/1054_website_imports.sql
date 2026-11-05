-- 1054_website_imports
--
-- Knowledge import from a business's own website: the current import of
-- each business (its address, how far the worker got reading up to 15
-- pages, what it found and why it failed). A tenant collection with
-- row-level security; the one document of a business is found by its
-- derived id (one current import per business), so no lookup columns are
-- needed. The drafts an import finds are ordinary knowledge items
-- (switched off until the owner confirms them).

select workshop.create_document_collection('website_imports');
