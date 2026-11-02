# Backup failed

**Alert:** `backup_failed` (SEV2): the last off-site backup (`workshop
backup`, the daily cron job of `render.yaml`) failed, or the last
successful one is older than 26 hours (the job stopped). Every run is
recorded in the database (`maintenance_runs`) and shown on Admin → System
with its error. Sentry Crons watches the same job from outside.

## Check

1. Admin → System: the last backup, its error and its age.
2. The cron job's logs on Render: did it run, and how did it end?
3. The bucket (`BACKUP_S3_*`): credentials, quota, the provider's status.
4. The database: did `pg_dump` fail on a connection limit or a timeout?

## Mitigate and fix

- Fix the cause (credentials, a missing variable, a full bucket) and run
  the job by hand from Render ("Trigger run"); the alert resolves when it
  succeeds.
- Until a backup succeeds, Render's own daily snapshots remain the fallback
  ([backup-restore](../backup-restore.md)).

## Afterwards

Check that the next scheduled run succeeds, and that the monthly restore
drill (`restore-drill.yml`) restores the new archive.
