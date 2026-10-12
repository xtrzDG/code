# Audit chain broken

**Alert:** `audit_chain_broken` (SEV1): the daily `verify_audit_chain`
job found a hash chain of the audit log that no longer verifies. Admin →
Audit shows the chain's status; the owner's Settings → Audit tab shows
their business's.

Every business has its own chain and the platform one more (entries
without a business: sign-in failures, lockouts, sign-outs, key
rotations). Each entry stores its position, the previous entry's hash and
its own hash (SHA-256 of its canonical JSON); entries are appended under
the chain's advisory lock in the transaction that writes them (migration
1193). The application's database role cannot update or delete them.

## How it shows

The status names the first bad position and the problem:

| Problem | Meaning |
| --- | --- |
| `hash_mismatch` | an entry's content no longer matches its hash: edited in the database |
| `link_broken` | an entry's previous hash is not the entry before it: an entry replaced |
| `position_gap` | a position is missing: an entry deleted |
| `head_lost` | the last verified entry is gone or changed since the previous check |
| `checkpoint_mismatch` | entries the retention purge removed are back, or the checkpoint was edited |

None of these happens through the application. A broken chain means
someone with the database owner's or a superuser's rights changed the
table, a restore mixed two backups, or a bug wrote outside the chain.

## Check

1. Admin → Audit: which chains are broken and where. The job's log line
   names the chain and position (never the entry's content).
2. Postgres: `select document from audit_log_entries where doc_chain_key =
   '<chain>' and doc_chain_position between <n> - 2 and <n> + 2 order by
   doc_chain_position;` (as the migration role). Compare with the last
   backup taken before the break (docs/operations/backup-restore.md).
3. Who had owner or superuser access: the provider's audit trail of the
   database (Render → `workshop-db` → Events and logs), deploys and
   migrations of the period.

## Mitigate

- Treat it as a possible breach until explained: start
  [data-breach](data-breach.md), restrict database owner credentials,
  rotate `DATABASE_URL` passwords.
- Do not "repair" the chain in place: the broken entry is the evidence.
  Export the affected rows and the backup's copy for the incident notes.

## Fix

- A restore that mixed backups: restore the whole database from one
  backup (docs/operations/backup-restore.md).
- Once explained and recorded, the next check reports the chain as it is;
  a chain stays broken until the bad rows are restored from a backup.

## Retention purge

Old entries leave only through `workshop purge-audit-log
--older-than-days N` (at least 365), run by an operator with the
migration role's `DATABASE_URL`, never from `preDeployCommand`. It
removes each chain's oldest entries in batches and records the chain's
checkpoint (the last removed position and its hash), so the rest of the
chain still verifies; each purged chain gets a `retention_purge` entry.

## Afterwards

- Postmortem with the timeline from the database provider's logs.
- If an application path wrote outside the chain, add a test that fails
  without the fix (tests/compliance/audit_chain/).
