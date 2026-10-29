-- 1164_post_deploy_data_tasks
--
-- Post-deploy data tasks that run themselves (W16-DATA-TASKS-ENUM-GATE):
-- after a release, the batch worker rewrites documents of older schema
-- versions and fills trigger-kept lookup columns of older rows in keyset
-- batches, once no worker of another release is left, instead of an
-- operator running `workshop migrate-documents` and `workshop
-- backfill-lookup` by hand (docs/operations/deploys.md).
--
-- data_task_states (platform collection): the progress of one task (its
--   keyset position, counts, failures), stored under the task's key of the
--   data-task registry (app/registries/maintenance/). Every read is by
--   those keys (`get_many`), so the table needs no lookup column; it holds
--   one row per registry entry, a few dozen.
--
-- The table is new and empty: online-safe as it is.

select workshop.create_document_collection('data_task_states');
