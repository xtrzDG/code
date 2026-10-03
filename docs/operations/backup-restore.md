# Backups, restore drills and key rotation

How customer data survives a lost database, a lost hosting account or a
leaked key, how recovery is proven every week, and what to do on the day it
is needed. The launch guide (`docs/LAUNCH.md`, section 4.11, in Russian)
covers the first setup; this page is the reference and the runbook.

## Objectives

| Objective | Target | Met by |
| --- | --- | --- |
| RPO, database lost or corrupted | 5 minutes | Render's point-in-time recovery (continuous WAL archive, the plan's window) |
| RPO, Render account or region lost | 24 hours | the nightly off-site backup (`workshop backup`) |
| RTO, any of the above | 2 hours | a new database, one restore, `workshop migrate`, a deploy (runbook below) |
| Proof | every week | the restore drill restores production's newest backup and checks it |

What each scenario costs:

| Scenario | Recover from | Data lost |
| --- | --- | --- |
| A bad migration, a mass delete, a bug that wrote nonsense | Render point-in-time recovery to just before it | none to minutes |
| The database is gone or unreadable | Render point-in-time recovery or Render's daily snapshot | minutes |
| The Render account, the region or Render itself is gone | the off-site backup | since the last night (at most 24 h) |
| The backup bucket's key leaked | nothing to restore: archives are age-encrypted; revoke the key | none |
| `ENCRYPTION_KEY` leaked | key rotation (below) | none |
| The drill's private age key is lost | the escrow key (below) | none |

## Layers

1. **Render Postgres** (`workshop-db`, Frankfurt): daily snapshots and
   point-in-time recovery for the plan's window (the database's Recovery
   tab shows it). First choice for anything that happened inside Render.
2. **Off-site backup**, the cron service `workshop-backup` (`render.yaml`):
   every night at 01:17 UTC `workshop backup` writes an encrypted dump to an
   S3-compatible bucket in the EU **at another provider**. It survives the
   loss of the Render account, the region or the provider.
3. **Restore drill**, `.github/workflows/restore-drill.yml`: proves the
   backups restore. Nightly it backs up and restores a seeded throwaway
   database with this checkout's code; on Mondays it restores production's
   newest backup into a throwaway Postgres 16.

## The backup (`workshop backup`)

`app/gateways/cli/backup.py` →
`app/use_cases/maintenance/backups/create_database_backup_use_case.py`.

1. A read-only REPEATABLE READ transaction on `DATABASE_URL` exports its
   snapshot; the rows of every table of the `workshop` schema are counted in
   it, together with the applied migrations, the tables under forced
   row-level security and the number of policies.
2. `pg_dump --format=custom --snapshot=<that snapshot>` dumps exactly the
   counted state while the platform keeps writing. It runs as the
   application role with the application's own RLS switch
   (`app.bypass_rls=on` for that session only, `--enable-row-security`),
   so no superuser or BYPASSRLS role exists anywhere. The password goes in
   `PGPASSWORD`, never on the command line.
3. The dump is encrypted in the [age](https://age-encryption.org/v1)
   format (X25519, ChaCha20-Poly1305 in 64 KiB chunks;
   `app/utilities/security/age/`) to every public key of
   `BACKUP_AGE_PUBLIC_KEY`, and the plaintext dump is deleted at once. The
   archive opens with the `age` command line tool too
   (`tests/backups/test_age_cli_interop.py`).
4. The archive is uploaded to `<BACKUP_S3_PREFIX><YYYY>/<MM>/<time>Z.pgdump.age`
   (one PUT up to 32 MiB, a multipart upload above; an aborted upload is
   cleaned up), then its manifest `<time>Z.manifest.json`: the archive's
   size and SHA-256 and the snapshot's counts. Table names and counts only,
   never row contents. The manifest goes last, so an archive with a
   manifest is complete.
5. Retention keeps the newest backup of each of the last
   `BACKUP_KEEP_DAILY` (30) days and of each of the last
   `BACKUP_KEEP_MONTHLY` (12) months, and deletes every other archive under
   the prefix with its manifest. Anything else in the bucket is never
   touched.

Every run checks in to Sentry Crons (monitor `database-backup`, daily, an
hour of margin) and reports a failure to Sentry; the cron's log in Render
shows the uploaded key, the snapshot's size and what retention deleted.
Exit codes: 0 done, 1 failed, 2 not configured.

**The bucket.** Private, in the EU, at another provider than Render
(AWS `eu-central-1`, Hetzner, Scaleway, Cloudflare R2 with the EU
jurisdiction). Versioning on, with a lifecycle rule that expires noncurrent
versions after 14 days (a leaked writer key cannot erase the history at
once) and aborts incomplete multipart uploads after 2 days. Two keys:
the cron's (put, list, delete under the prefix; set on `workshop-backup`
only, never on the API or the worker) and the drill's (get and list only).

## Keys and custody

**Backup keys (age).** Generated with `age-keygen` on an operator's
machine, never on a server.

- The **drill identity**: its private key is the GitHub environment secret
  `BACKUP_AGE_IDENTITY` of the `backup-drill` environment; nothing else
  holds it.
- The **escrow identity**: printed and sealed in the company safe, a second
  copy in the founders' password manager vault; two named people can reach
  it. It opens every backup when the drill key is lost or compromised.
- `BACKUP_AGE_PUBLIC_KEY` lists both public keys. Production holds public
  keys only: the backup job can write archives, never read them.
- Replacing a backup key: add the new public key, wait until every kept
  archive was written after the change (12 months for the monthly copies),
  then remove the old one. Keep the old private key until then.

**The encryption key ring** (`ENCRYPTION_KEYS`, then `ENCRYPTION_KEY`).
It seals channel credentials and Google Calendar tokens (Fernet, through
MultiFernet), derives the Telegram webhook secrets, signs notification
links and derives the recordings' keys. The first key seals and signs
everything new; the others only open and verify what they sealed.

- The keys live in the Render env group `workshop-backend` and, as an
  escrow copy, in the founders' password manager vault.
- A backup holds the secrets sealed with the keys of its night: keep every
  retired key in escrow for 12 months (the oldest monthly backup), then
  destroy it.
- A leaked key alone opens nothing: the ciphertexts are in the database.
  Rotate anyway; if the database leaked as well, also revoke the channel
  tokens at the providers.

## Key rotation

1. Generate a key:
   `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
2. In the env group `workshop-backend` set `ENCRYPTION_KEYS` to the new key
   (comma-separated, newest first; `ENCRYPTION_KEY` keeps following as the
   oldest). The API and the worker redeploy. From now on everything new is
   sealed and signed with the new key; old secrets still open, Telegram
   webhooks registered with the old key's secret are still accepted, and
   the platform bot's webhook is registered again at the API's start.
3. As a platform admin: `POST /v1/admin/security/encryption-keys/rotate`
   (202, audited; 409 while a run is going). The worker's
   `rotate_encrypted_secrets` job walks every business: each secret is
   sealed again with the current key and written back only if it did not
   change meanwhile; every active Telegram bot's webhook is registered again
   with the current key's secret.
4. `GET /v1/admin/security/encryption-keys` shows the run: `secrets_rotated`
   and `secrets_current`, `secrets_unreadable` (no key of the ring opens
   them: the owner must reconnect that channel), `webhooks_failed` (run it
   again later). The old key may go only when a run ends `done` with both
   at zero.
5. Wait until the last notification link signed with the old key expired
   (7 days) and, with recordings in the bucket, until
   `RECORDING_RETENTION_DAYS` passed (recordings sealed with the old key
   open while it is in the ring). Then set `ENCRYPTION_KEY` to the new key
   and delete `ENCRYPTION_KEYS`.
6. Move the retired key to escrow (above).

## The restore drill (`workshop restore-check`)

`app/gateways/cli/restore_check.py` →
`app/use_cases/maintenance/backups/check_backup_restore_use_case.py`.

1. The newest archive (or `--archive <key>`) and its manifest are
   downloaded; the archive's size and SHA-256 must match the manifest.
2. It is decrypted with `BACKUP_AGE_IDENTITY` (a changed, cut or extended
   archive does not open) and restored with
   `pg_restore --no-owner --no-acl --single-transaction --exit-on-error`
   into a new database `restore_drill_<random>` of the throwaway server in
   `RESTORE_CHECK_DATABASE_URL` (a role that may create databases; never
   production's server).
3. Checks, each failure one line of the report:
   - every table has exactly the dumped number of rows, no table is missing
     or extra, the RLS tables and policies are the dumped ones;
   - the migrations are this checkout's (same names and checksums, no gap;
     newer ones are listed as pending, a restore applies them);
   - row-level security still isolates businesses: as a role bound by RLS
     (a throwaway NOLOGIN role when the restoring role is a superuser),
     no table shows a row without a business scope, and in one business's
     scope every table shows exactly that business's rows; a business table
     without RLS fails too;
   - the newest backup is at most `BACKUP_MAX_AGE_HOURS` (26) old.
4. The scratch database and the probe role are dropped (`--keep-database`
   keeps the database: that is a real restore, below).

Sentry Crons monitor `restore-drill` (weekly, with margin) gets the
production drill's check-ins; a failed check is reported as an error with
the list. Exit codes: 0 the backup restores, 1 a check or the restore
failed, 2 not configured.

**The workflow** (`.github/workflows/restore-drill.yml`):

- `round-trip`, nightly, on demand and on pull requests touching the
  backup code: a Postgres 16 service, the application role, `workshop
  migrate`, `workshop seed-load` for realistic rows, `workshop backup` into
  a local S3 server, `workshop restore-check`, and the archive opened once
  more with the `age` tool. Proves the tooling of the code about to ship.
- `production`, Mondays and on demand: checks out `release` (the code
  production runs), restores production's newest backup into a throwaway
  Postgres 16 and checks it. Runs only when the repository variable
  `BACKUP_S3_BUCKET` is set; its secrets (the drill's read-only bucket key,
  `BACKUP_AGE_IDENTITY`, `SENTRY_DSN`) live in the environment
  `backup-drill`.

Both install the Postgres 17 client: the image's `pg_dump` is Debian's 17,
and an archive opens only with a `pg_restore` at least as new.

## Restore runbook

Decide first: did it happen inside Render (bad data, lost database) or is
Render itself gone?

**A. Inside Render: point-in-time recovery** (RPO minutes, RTO under 1 h).
Render dashboard → `workshop-db` → Recovery → restore to just before the
incident into a new database; set the new database's internal connection
string as `DATABASE_URL` of `workshop-api`, `workshop-worker` and
`workshop-backup`; deploy; check below.

**B. Render unavailable or the window passed: the off-site backup**
(RPO 24 h, RTO 2 h).

| Step | Time |
| --- | --- |
| 1. A new Postgres 16 in the EU (Render in another account, or any EU provider); create the application role (neither superuser nor BYPASSRLS) with `CREATEDB` for the restore | 15 min |
| 2. On a trusted machine with the drill or escrow identity: restore the newest backup (below) | 30–60 min (about 10 min per GB of dump) |
| 3. `workshop migrate` against the restored database (migrations newer than the backup) | 5 min |
| 4. Point `DATABASE_URL` of the API, the worker and the backup cron at it; `ENCRYPTION_KEYS`/`ENCRYPTION_KEY` must hold the keys of the backup's night; deploy | 20 min |
| 5. Checks below; tell owners what happened since the backup | 15 min |

Restoring with this code base (it checks everything the drill checks and
keeps the database):

```bash
export BACKUP_S3_ENDPOINT_URL=... BACKUP_S3_REGION=... BACKUP_S3_BUCKET=...
export BACKUP_S3_ACCESS_KEY_ID=... BACKUP_S3_SECRET_ACCESS_KEY=...   # the drill's key
export BACKUP_AGE_IDENTITY="$(grep AGE-SECRET-KEY key.txt)"
export RESTORE_CHECK_DATABASE_URL=postgresql://app_role:...@new-host:5432/postgres
uv run python -m app.gateways.cli.restore_check --keep-database
# prints "Restored <archive> ... into restore_drill_<id> (kept)."
psql "$RESTORE_CHECK_DATABASE_URL" -c 'alter database restore_drill_<id> rename to workshop'
```

Restoring by hand, without this code base:

```bash
aws s3 cp s3://<bucket>/workshop/2026/10/20261003T011700Z.pgdump.age .   # or any S3 tool
aws s3 cp s3://<bucket>/workshop/2026/10/20261003T011700Z.manifest.json .
sha256sum 20261003T011700Z.pgdump.age      # must equal archive_checksum of the manifest
age --decrypt --identity key.txt --output dump.pgc 20261003T011700Z.pgdump.age
createdb --host new-host --username app_role workshop
pg_restore --host new-host --username app_role --dbname workshop \
  --no-owner --no-acl --single-transaction --exit-on-error dump.pgc
```

Restore as the application role so that it owns the tables (row-level
security is forced, so it binds the owner as well); `pg_restore` 17 or
newer.

**Checks after either path.** `GET /readyz` answers 200 (database reached,
every migration applied); `scripts/smoke.sh` against the API passes; an
owner signs in and sees yesterday's conversations; a test message through
a Telegram bot gets an answer. Telegram and Meta retry undelivered
webhooks for a while, so part of the outage's messages arrive by
themselves; staff should look at the channels for the rest.

## Rehearsing the runbook

The weekly drill covers path B's restore and checks. Once a quarter,
time a full path B on a copy (steps 1–5 into a separate Render account
or a local machine) and write the measured RTO into this page's table.
