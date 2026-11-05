# Bad deploy

**Signals:** errors climb in Sentry right after a release, the deploy
smoke test fails (`.github/workflows/deploy-smoke.yml`), alerts fire
within minutes of a deploy, owners report a broken flow.

## Decide (5 minutes)

- Did the trouble start with the deploy (Render → Events, the release in
  Sentry's tags, `release` on worker pulses on `/admin/system`)? If yes,
  roll back first and investigate after: rolling back is the cheapest
  mitigation and is always safe (`../deploys.md`, "Two releases at once").

## Roll back

Follow `../deploys.md`, "Rollback":

1. Render → `workshop-api`, `workshop-worker`, `workshop-cabinet` → Events
   → the last good deploy → Rollback (API, then worker, then cabinet).
2. Move `release` to the good commit so it is not deployed again:
   `git push --force-with-lease origin <good-commit>:release`.
3. Run the smoke workflow against production; watch Sentry and
   `/admin/system` (alerts, lanes, dead letters).
4. Documents the bad release wrote stay readable; never run
   `migrate-documents` before the fix. A SQL migration is undone only by a
   new migration.

## Recover

- Retry dead letters the bad release produced (`/admin/system`), once the
  good release runs.
- Fix forward on `main`; staging and the smoke test promote it.

## Afterwards

- Postmortem for SEV1/SEV2: which check should have caught it (a unit
  test, an e2e flow, the smoke test, staging) and add it.
