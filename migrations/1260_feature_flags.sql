-- 1260_feature_flags
--
-- The feature flags of staged rollouts (REL-08, docs/operations/deploys.md,
-- "Staged rollouts"): one row per flag of the registry
-- (app/utilities/feature_flags/feature_flag_catalog.py), stored under its
-- name and read by the names a release knows, at request time through the
-- flag gate. A platform collection: a flag names businesses only in its
-- inclusion and exclusion lists, and the tenant role holds no privilege
-- on it (1200).
--
-- Online-safe (migrations/README.md): one transaction; the table is new
-- and empty, and no existing table changes.

select workshop.create_platform_collection('feature_flags');
