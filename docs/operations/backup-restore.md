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
| Proof | every week | the restore drill restores production's newest backup and checks it, and writes its timings to the run's report |
| Measured | every quarter | a timed full path B restore, recorded in `docs/operations/restore-test-report.md` |

The customer-facing commitments (`docs/legal/drafts/sla.md`, a draft for
the owner to adopt) promise less than these internal targets: RPO 15
minutes, RTO 4 hours, call forwarding switched on within 15 minutes.

**Call recordings are not in the backups.** The backup is the database
dump only. Recordings live in their own EU bucket (`RECORDINGS_S3_*`),
each sealed with a key of its business; that bucket is set up with
object versioning and a rule that expires noncurrent versions after 30
days (an overwritten or deleted recording stays recoverable that long,
`docs/operations/go-live.md` section 6) and relies on the provider's own
durability. Losing that bucket loses the recordings; the database,
transcripts and call summaries come back from the backups. This is a
decision, not a gap: recordings are short-lived (the owner's retention),
large, and the transcript keeps what was said.

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
   database with this checkout's code on a GitHub-hosted runner (synthetic
   data only); every week production's newest backup is restored into a
   throwaway Postgres 16 on the platform's drill machine in the EU (below).

## The backup (`workshop backup`)

`app/gateways/cli/backup.py` →
`app/use_cases/maintenance/backups/create_database_backup_use_case.py`.

1. A read-only REPEATABLE READ transaction on `DATABASE_URL` exports its
   snapshot; the rows of every table of the `workshop` schema are counted in
   it, together with the applied migrations, the tables under forced
   row-level security and the number of policies.
2. `pg_dump --format=custom --snapshot=<that snapshot>` dumps exactly the
   counted state while the platform keeps writing. It runs as the
   migration role, the tables' owner (`DATABASE_URL`): since migration
   1200 a member of `workshop_platform`, whose policies show it every row
   (`--enable-row-security`; the session still sets `app.bypass_rls=on`
   for databases before 1200), so no superuser or BYPASSRLS role exists
   anywhere. The password goes in
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
Each run is also recorded in the database it dumped (`maintenance_runs`:
how it ended, the archive, its size and rows, or the first line of the
error), so `/admin/system` shows the last backup and marks it overdue when
it failed or is older than `BACKUP_MAX_AGE_HOURS`. Recording is best
effort: a database that refuses the row never fails the backup.
Exit codes: 0 done, 1 failed, 2 not configured.

**The bucket.** Private, in the EU, at another provider than Render
(AWS `eu-central-1`, Hetzner, Scaleway, Cloudflare R2 with the EU
jurisdiction), in **its own account** whose root credentials are in the
vault and on no server. It is immutable for the whole retention window:

- **Object Lock** is enabled when the bucket is created (it cannot be
  added later on most providers; it turns versioning on), with a default
  retention in **compliance mode of 31 days**: no key, the account's root
  included, can remove an archive version for its first 31 days.
- A lifecycle rule expires **noncurrent versions after 400 days**, never
  sooner: a delete by retention or by a leaked key only hides an archive
  behind a delete marker, and its version stays recoverable for more than
  the 12 months of monthly copies. Another rule aborts incomplete
  multipart uploads after 2 days. The price is storage: each expired
  daily archive is kept about 13 months longer (about 400 archives in
  all; at 1 GB a dump, well under 10 euros a month at EU object-storage
  prices).
- Proof, at setup and then once a year (`docs/operations/go-live.md`,
  section 6): with the cron's key, `aws s3api delete-object --bucket <b>
  --key <archive> --version-id <id>` must answer AccessDenied, and with
  the drill's and the ledger's keys every delete must too. Write the date
  into `docs/operations/restore-test-report.md`.

Three keys:
the cron's (put, list, delete under the prefix; set on `workshop-backup`
only, never on the API or a worker), the drill's (get and list only), and
the deletion ledger's (put, get and list under
`<BACKUP_S3_PREFIX>deletion-ledger/` only, no delete; set on
`workshop-batch-worker`, which deletes businesses on its default lane and
records customers' erasures there too).

## Keys and custody

**Backup keys (age).** Generated with `age-keygen` on an operator's
machine, never on a server.

- The **drill identity**: its private key is `BACKUP_AGE_IDENTITY` on the
  drill machine (below, "Where the production drill runs"); the GitHub
  environment `backup-drill` holds a copy only while the workflow's
  production job is switched on (`RESTORE_DRILL_ON_GITHUB`); nothing else
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
3. As a platform admin: cabinet → Encryption keys (`/admin/security`) →
   Re-encrypt stored tokens, or `POST /v1/admin/security/encryption-keys/rotate`
   (202, audited; 409 while a run is going). The worker's
   `rotate_encrypted_secrets` job walks every business: each secret is
   sealed again with the current key and written back only if it did not
   change meanwhile; every active Telegram bot's webhook is registered again
   with the current key's secret.
4. The page (or `GET /v1/admin/security/encryption-keys`) shows the run: `secrets_rotated`
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
   archive does not open) and restored: `pg_restore --no-owner --no-acl`
   writes its SQL script and `psql --single-transaction` with
   `ON_ERROR_STOP` runs it (a cut script is never committed). pg_restore 17
   opens the script with `SET transaction_timeout = 0;`, which Postgres 16
   does not know, so that line of the preamble is left out for older
   servers. The target is a new database `restore_drill_<random>` of the
   throwaway server in
   `RESTORE_CHECK_DATABASE_URL` (a role that may create databases and
   roles, CREATEDB and CREATEROLE; never production's server). The dumped
   policies name the groups `workshop_tenant` and `workshop_platform` of
   migration 1200, so the drill creates them on that server before the
   restore when they are missing; a role without CREATEROLE needs an
   administrator to create them once and grant it `workshop_tenant` with
   ADMIN OPTION.
3. Checks, each failure one line of the report:
   - every table has exactly the dumped number of rows, no table is missing
     or extra, the RLS tables and policies are the dumped ones;
   - the migrations are this checkout's (same names and checksums, no gap;
     newer ones are listed as pending, a restore applies them);
   - row-level security still isolates businesses: the restoring role
     (the owner, a member of `workshop_platform`) counts one business's
     rows, then a throwaway NOLOGIN member of `workshop_tenant` (the
     tenant pool's kind of role) switches `app.bypass_rls` on, as an
     injected statement would, and must still see no row without a
     business scope and, in that business's scope, exactly its rows in
     every table; a business table without RLS fails too. A backup from
     before 1200 is probed as before: as a role bound by RLS (a throwaway
     NOLOGIN role when the restoring role is a superuser), without the
     switch;
   - the newest backup is at most `BACKUP_MAX_AGE_HOURS` (26) old.
   Then the deletion ledger is applied to the restored database (its copy
   in the bucket, `<BACKUP_S3_PREFIX>deletion-ledger/<business id>.json`,
   one object per deleted business written when the deletion began, and
   the database's own `business_deletions`): every row of those
   businesses is deleted again, but the audit log and issued invoices,
   and the report says "Deletion ledger: N deleted businesses, M of their
   rows deleted again, K left." A row left fails the drill. Retention
   never removes the ledger's objects (they are no archives).
   The ledger of erased customers beside it is counted: "Erasure ledger:
   N erased customers, M of them with their data in this backup". M is
   the number of customers erased after the backup was taken; the drill
   leaves them (an erasure reaches messages, calls, recordings and the
   sub-processors' copies, which only the application's own erasure
   does), and after a real restore the worker erases them again (below).
4. The scratch database and the probe role are dropped (`--keep-database`
   keeps the database: that is a real restore, below).

Sentry Crons monitor `restore-drill` (weekly, with margin) gets the
production drill's check-ins; a failed check is reported as an error with
the list. Where the drill runs with `DATABASE_URL` it records its run for
`/admin/system` like the backup; the drill machine and the GitHub workflow
cannot reach Render's private database, so their drills show in Sentry
Crons and their reports only. Exit
codes: 0 the backup restores, 1 a check or the restore failed, 2 not
configured.

**The workflow** (`.github/workflows/restore-drill.yml`):

- `round-trip`, nightly, on demand and on pull requests touching the
  backup code: a Postgres 16 service, the application role, `workshop
  migrate`, `workshop seed-load` for realistic rows, `workshop backup` into
  a local S3 server, `workshop restore-check`, and the archive opened once
  more with the `age` tool. Proves the tooling of the code about to ship.
- `production`, Mondays and on demand: checks out `release` (the code
  production runs), restores production's newest backup into a throwaway
  Postgres 16 and checks it. **Off by default**: it runs only when the
  repository variable `BACKUP_S3_BUCKET` is set and
  `RESTORE_DRILL_ON_GITHUB` is `true`, because it decrypts production's
  data on a GitHub-hosted runner, a transfer to GitHub that the DPA's list
  does not name. Turn it on only after GitHub is announced as a
  sub-processor (30 days' notice, its DPA with DPF and SCCs); its secrets
  (the drill's read-only bucket key, `BACKUP_AGE_IDENTITY`, `SENTRY_DSN`)
  live in the environment `backup-drill`.

Both append the drill's report to the run's summary (`--report`): the
archive, when it was taken, when the drill started and finished, how long
the download, restore and checks took, how old the backup was (the data a
restore at that moment would lose) and the failed checks.

**Where the production drill runs.** Production's data is decrypted only
in the EU, on the platform's **drill machine**: a small VM at an EU
provider other than Render (e.g. Hetzner or Scaleway in Germany), with
Postgres 16 and pgvector for the scratch database, this repository's
`release` checkout, the drill's read-only bucket key and
`BACKUP_AGE_IDENTITY`, and nothing else of the platform. A weekly timer
(Monday 03:41 UTC) first brings the checkout to `release` (`git fetch`
with a read-only deploy key, `git checkout --detach origin/release`,
`uv sync --frozen`), so the drill runs the code production runs, then
`uv run python -m app.gateways.cli.restore_check --report <dated file>`
with `SENTRY_DSN` set, so Sentry Crons `restore-drill` sees each run and
the reports stay on the machine for the quarterly record. GitHub-hosted
runners restore synthetic data only, so GitHub is no sub-processor
(`docs/operations/vendor-register.md`, "GitHub and the restore drill").
Until the machine exists, the weekly production proof does not run (an
owner action of `docs/operations/go-live.md`, section 6).

Not on Render, because the drill's key opens twelve months of history,
customers erased since included: kept off Render, a compromise of the
Render account reaches today's data, not the backups'. But the machine's
provider sees production's data decrypted, so it is a sub-processor like
any other: **before the drill key reaches the machine, its provider is in
the DPA's list for this purpose**. The simplest is the backup bucket's own
provider: the list's EU object storage entry (`app/registries/legal/`)
then names the weekly restore test of the backups as a purpose of its own,
announced 30 days ahead like any change of the list (DPA 8.3). A provider
the list does not name never receives `BACKUP_AGE_IDENTITY`.

Both install the Postgres 17 client: the image's `pg_dump` is Debian's 17,
and an archive opens only with a `pg_restore` at least as new.

Both run Postgres 16 **with pgvector** (`pgvector/pgvector:0.8.0-pg16`).
Once an administrator enabled the knowledge embeddings in production
(`create extension vector;`, then `select
workshop.enable_knowledge_embeddings();`, docs/LAUNCH.md), every dump holds
`CREATE EXTENSION IF NOT EXISTS vector` and a `vector` column, and the
single-transaction restore stops at the first statement a server without
pgvector refuses. `round-trip` enables the embeddings the same way after
`workshop migrate`, so the nightly drill restores such a dump too.

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
| 1. A new Postgres 16 **with the pgvector extension available** in the EU (Render in another account, or any EU provider); as a superuser run `create extension vector;` in `template1` (so every database the restore creates has it: the application roles may not create this untrusted extension, and the dump's `CREATE EXTENSION IF NOT EXISTS vector` is then a no-op); create the migration role (neither superuser nor BYPASSRLS) with `CREATEDB` and `CREATEROLE` for the restore, and the groups and login roles of `docs/operations/deploys.md`, "Database roles" | 15 min |
| 2. On a trusted machine with the drill or escrow identity: restore the newest backup (below) | 30–60 min (about 10 min per GB of dump) |
| 3. `workshop migrate` against the restored database (migrations newer than the backup) | 5 min |
| 4. Point `DATABASE_URL` of the API, the worker and the backup cron at it, and `DATABASE_URL_TENANT` and `DATABASE_URL_PLATFORM` of the API (the workers copy them) at the new login roles; `ENCRYPTION_KEYS`/`ENCRYPTION_KEY` must hold the keys of the backup's night; deploy | 20 min |
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
createdb --host new-host --username app_role workshop   # has vector from template1 (step 1)
pg_restore --no-owner --no-acl --file=- dump.pgc \
  | sed '1,40{/^SET transaction_timeout = 0;$/d}' \
  | psql --host new-host --username app_role --dbname workshop \
      --no-psqlrc --single-transaction --set ON_ERROR_STOP=1
```

Restore as the migration role so that it owns the tables (row-level
security is forced, so it binds the owner as well); create the groups
`workshop_tenant` and `workshop_platform` first (the dumped policies name
them, and the restore stops without them) and grant `workshop_platform`
to the migration role; `pg_restore` 17 or newer. The `sed` leaves out the one setting of pg_restore 17's preamble
that a Postgres 16 server refuses (`unrecognized configuration parameter
"transaction_timeout"`); on Postgres 17 it may stay.

**Deleted businesses after either path.** A backup older than a
business's deletion brings that business back. The worker's daily
`reapply_deletion_ledger` deletes it again within a day of the restore
(the ledger's copy in the bucket names every deletion since;
`workshop-batch-worker` holds the bucket settings and the ledger's key);
a restore through
`restore-check --keep-database` has already applied the ledger.

**Erased customers after either path.** A backup older than a
customer's erasure (an owner's erasure of a customer's data, Customers →
a customer → Data requests; GDPR article 17) brings their data back. Each erasure is recorded outside the
database: the queued job `record_contact_erasure` (retried until the
bucket takes it) writes one object per erased customer,
`<BACKUP_S3_PREFIX>deletion-ledger/contacts/<business id>/<contact id>.erasure`
(ids and the moment only, nothing personal; `.erasure`, so the business
ledger never reads it as a deletion). The worker's daily
`reapply_contact_erasures` (`ReapplyContactErasuresUseCase`, the batch
worker) reads every record and erases again each customer whose contact
is back with its data, with the same erasure as the owner's, audited as a
deletion without an actor; a customer still erased, or gone with their
business, is left alone, and a failed erasure fails the run, which is
retried the next day. A daily job runs once per UTC day, and the restored
database may already hold today's run; to apply the ledger at once
(step 5 of path B, and after a point-in-time recovery), delete that run
as the migration role and the next worker tick runs it:

```sql
delete from workshop.periodic_job_runs
where document ->> 'job_name' = 'reapply_contact_erasures'
  and document ->> 'period_key' = to_char(now() at time zone 'utc', 'YYYY-MM-DD');
```

The drill's "Erasure ledger" line says how many customers that run will
erase. Two gaps remain. The queued job lives in the database, so an
erasure whose record had not reached the bucket yet (normally seconds,
the batch worker's next claim) is lost with the database it was made in,
audit entry included; after a point-in-time recovery, look for
`DELETE /v1/businesses/{id}/contacts/{contact id}` answered 204 in the
API's request log of the lost minutes and erase those customers again
(the owner, Customers → the customer → Data requests). A record the
bucket kept refusing stays among the dead jobs on `/admin/system`: retry
it there.

**Checks after either path.** `GET /readyz` answers 200 (database reached,
every migration applied); `scripts/smoke.sh` against the API passes; an
owner signs in and sees yesterday's conversations; a test message through
a Telegram bot gets an answer. Telegram and Meta retry undelivered
webhooks for a while, so part of the outage's messages arrive by
themselves; staff should look at the channels for the rest.

## Rehearsing the runbook

The weekly drill covers path B's restore and checks. Once a quarter,
time a full path B on a copy (steps 1–5 into a separate Render account
or a local machine in the EU) and record it with the template of
`docs/operations/restore-test-report.md`: the achieved RPO and RTO, the
integrity checks (the drill's counts and isolation probes, three sample
businesses opened in the restored cabinet, three recordings played from
the recordings bucket) and what the runbook got wrong, fixed in this page
the same day.
