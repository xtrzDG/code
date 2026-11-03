# Restore test reports

The quarterly evidence that the backups restore in time: a full path B
restore (`docs/operations/backup-restore.md`, "Restore runbook") into an
isolated environment, timed, with its integrity checks, and the yearly
proof that no application or deploy key can delete a backup. The weekly
drill's own timings are in each run's summary of
`.github/workflows/restore-drill.yml` (`workshop restore-check --report`);
this page is the record a customer or an auditor reads.
`tests/legal/test_restore_test_report.py` fails when no restore test was
held or planned within 92 days, when a planned one passed more than a
month ago without being recorded, or when a held one lacks its measures.

## How to run one

1. Pick the newest off-site archive; note when it was taken.
2. Start the clock. Follow path B, steps 1–5, into a separate Render
   account or a local machine in the EU, never production's server.
3. Stop the clock when `GET /readyz` answers 200 on the restored API.
4. Checks: the drill's lines (every table's rows, the RLS probes, the
   ledgers); three businesses opened in the restored cabinet (bookings,
   conversations, settings as yesterday); three recordings of those
   businesses played from the recordings bucket (they are not in the
   backup, so this proves the keys and the bucket still match).
5. Achieved RPO: the time between the archive and the moment it was
   picked. Achieved RTO: the clock. Compare with the targets of
   `docs/operations/backup-restore.md` ("Objectives": RPO 24 h and RTO 2 h
   for path B) and the SLA draft (`docs/legal/drafts/sla.md`).
6. Fix every step the runbook got wrong the same day, then add a row
   below and delete the restored copy.

## Template

Copy into the record as one row:

| Date | Kind | Archive taken | RPO achieved | RTO achieved | Integrity | Runbook changes | By |
| --- | --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | full path B restore | YYYY-MM-DD HH:MM UTC | h:mm | h:mm | rows and RLS OK; 3 businesses; 3 recordings | none, or what changed | name |

Kinds: `full path B restore` (quarterly), `delete denied` (yearly: with
the cron's, the drill's and the ledger's keys, deleting an archive version
answered AccessDenied, and a failed backup run alerted in Sentry), and a
planned one, whose date carries "(planned)" until it is held.

## Record

| Date | Kind | Archive taken | RPO achieved | RTO achieved | Integrity | Runbook changes | By |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-12-15 (planned) | full path B restore and delete denied, after the bucket and the EU runner exist (`docs/operations/go-live.md`, section 6) | | | | | | the founder |
