# Deploys, schema changes and rollbacks

How a commit reaches production, what a change must respect so that two
releases can run side by side, and how to roll back. The launch guide
(`docs/LAUNCH.md`, in Russian) covers the first setup on Render; this page
is for every release after it.

## The pipeline

```
pull request ──► CI (ci.yml: backend, cabinet, images, security, e2e)
      │ merge
      ▼
    main ──► staging (render.staging.yaml)   deploys only when every GitHub
      │       check of the commit passed (autoDeployTrigger: checksPass)
      │
      │      deploy-smoke.yml: scripts/smoke.sh against staging
      ▼ green
  release ──► production (render.yaml)       checksPass again, same commit
              deploy-smoke.yml: scripts/smoke.sh against production
```

- Every Render service (API, worker, cabinet) follows a branch with
  `autoDeployTrigger: checksPass`: a commit whose CI failed, or is still
  running, is never deployed.
- Staging follows `main`; production follows `release`. Only
  `.github/workflows/deploy-smoke.yml` moves `release`, and only forward
  (no force push) to a commit of `main` whose staging smoke test passed.
  Without staging, move it by hand after a green CI run:
  `git push origin <commit>:release`.
- API, worker and cabinet of one environment follow the same branch, so
  they always deploy the same commit. Never deploy one of them from another
  commit by hand: the worker runs the same document and job code as the API.
- `scripts/smoke.sh <api-url> [cabinet-url]` checks `/healthz`,
  `/readyz` (the database answers, the release's migrations are applied),
  `/widget.js`, `/v1/auth/login-options`, the cabinet's `/login` and,
  with `SMOKE_WIDGET_BUSINESS_ID`, a test chat through the website widget
  (`/v1/widget/{business_id}/config`, a message accepted with `202` and
  the worker's answer polled from `/v1/widget/{business_id}/messages`, so
  the check also proves the worker runs). CI runs the same script against
  the freshly built image.

### One-time setup

1. Create the `release` branch before production's Blueprint:
   `git push origin main:release`.
2. Create staging: Render → New → Blueprint → this repository, Blueprint
   path `render.staging.yaml`. Its env group `workshop-staging` sets
   `LLM_PROVIDER=scripted`: answers are one fixed sentence, nothing is sent
   to a model provider and nothing is paid per message. Give it its own
   addresses and sign-in channel (an e-mail mailbox is enough), never
   production's secrets.
3. In staging's cabinet create a smoke business with the website widget
   turned on and a live assistant (the widget refuses messages for a
   business that is not live, `409`); note its id.
4. GitHub → Settings → Environments: `staging` and `production`, with the
   variables `API_URL` and `CABINET_URL` (public addresses). For staging
   also `SMOKE_WIDGET_BUSINESS_ID` (step 3) and
   `SMOKE_EXPECT_REPLY=staging server`. Production gets no business id
   unless one real model answer per deploy is wanted.
5. Render reports each deploy of a GitHub-connected service to GitHub as a
   deployment whose environment is the service's name
   (`workshop-staging-api`, `workshop-api`); a successful one starts the
   smoke workflow. Check Actions after the first deploy: if no run
   appears, relay a Render deploy webhook as a repository dispatch
   `render-deploy-succeeded` with
   `{"service": "<service name>", "sha": "<commit>"}`, or start the
   workflow by hand (Run workflow → staging or production).
6. If `release` is a protected branch, allow GitHub Actions to push to it.
   Set the repository variable `PROMOTE_AFTER_STAGING_SMOKE=false` to
   promote by hand instead.

## Two releases at once

During a Render deploy the old and the new instances serve together for a
while; the worker restarts on its own schedule; a rollback brings back the
previous release on data the newer one wrote. Migrations
(`preDeployCommand: workshop migrate`) run before the new code starts, while
the old code still serves. So every release must work with:

- the database schema of the next release (migrations are additive),
- documents written by the previous and by the next release, and
- jobs queued by the other release: any worker may claim them. A new job
  name or payload field follows the same expand rule as documents (the
  workers learn it one release before the API queues it).

The overlap also doubles the processes: every pool and LISTEN connection
of the API and the worker is open twice for a while. The connection
budget (`docs/operations/capacity.md`, checked by
`tests/platform/test_connection_budget.py`) counts that; a third API
instance or a larger `DB_POOL_SIZE` goes through it.

Website widget messages are queued for the worker (`202`) since the
release that moved them out of the request. Across that release either
order works: an old API instance still answers in the request, a new one
answers `202`, workers of both releases answer queued widget messages, and
a widget script from before that release (cached in a visitor's browser)
takes the `202` as an answer without text and shows the answer at its
next poll, only without the typing dots meanwhile.

The release that moved every message to a customer into the outbox
(staff replies, booking reminders, call confirmations and links,
text-backs; PLAN 16.9.5) writes five new `OutboundMessageKind` values in
the release that introduces them, an exception to the enum rule below. An
old worker that claims the delivery job of such a row, or reads it among a
recipient's waiting messages, fails the job, and the job queue tries it
again (30 s backoff, five attempts) until a new worker takes it: replies
are late during the overlap, not lost. Before rolling back past that
release, let the outbox drain (no `pending` rows of the new kinds), or
the previous release cannot read them.

The release with device sessions, the admin team and support access
(PLAN 16.10.4) also writes new enum values in the release that introduces
them, an exception to the enum rule below: four `AuditAction` values
(`support_access_start`, `support_access_end`, `session_revoked`,
`platform_admin_changed`) and the staff link target `account_security`
(code 11 in signed staff links). An old API instance that lists an audit
log holding such an entry may fail that page until the overlap ends, and
an old instance refuses a new-device link: both only during the minutes
of the overlap, nothing is lost. Its new collections
(`platform_admins`, `support_access_grants`, migration 1103) and the new
optional session fields are unknown to the old release, which ignores
them; but an old instance does not check support grants, so a platform
admin may read a client's cabinet without an open look during the
overlap (it still needs two factors). Before rolling back past that
release, note that the admin rights fall back to the
`PLATFORM_ADMIN_*` lists.

The release with WhatsApp staff templates per language and channel health
(R9-CONNECT, `ChannelDocument` version 4) adds `whatsapp_staff_templates`,
`last_error_reason`, `last_inbound_at` and `last_outbound_at` and keeps
writing the single `whatsapp_staff_template` (the main language's
template, else the first), so the previous release still sends late staff
replies, in that one template. A version 3 row reads with its single
template as a list of one (upcaster). An old instance that saves a
WhatsApp channel during the overlap (a reconnect, the single-template
form, a delivery that marks it failing) writes version 3 without the new
fields: the list falls back to the single template and the owner adds the
other languages again; the activity times come back with the next
messages. `workshop migrate-documents --collection channels` after the
release is optional (reads upcast anyway).

The release that teaches the assistant from conversations ("Fix this
answer", bad rating reasons and the owner's checks, migration 1112) also
writes new enum values in the release that introduces them, an exception
to the enum rule below: autotest runs hold scenarios of the new kind
`owner_check` and the check codes `expected_text_missing`,
`forbidden_text_mentioned` and `no_lead_created`. An old API instance
that reads such a run (the autotest page, the go-live checklist) may fail
that request until the overlap ends, and an old worker that plays a run a
new instance planned fails the job, which the queue tries again until a
new worker takes it: nothing is lost. The new review fields of
conversations (`rating_reason`, `rated_message_id`, `improved_at`,
`awaits_improvement`), `correction_of` of knowledge items and the new
`autotest_cases` collection are unknown to the old release, which ignores
them; but an old instance that saves a conversation during the overlap (a
customer turn) writes it without them, so the reason of a bad rating given
just before may be lost and the conversation leaves "Answers worth
improving" (the rating itself stays). Before rolling back past that
release, let running autotests finish.

The storage layer makes the second part mechanical
(`app/adapters/storage/persisted_document_codec.py`): documents are
validated strictly everywhere they are built and written, carry their
`schema_version`, and on the storage read path unknown fields are ignored
(`extra="ignore"`, nested objects included) and older versions run through
the upcasters of `app/adapters/storage/document_upgrades.py`. What the code
cannot do for you are the rules below.

## Changing a stored document: expand, then contract

Never change a stored shape in a way the previous release cannot read.
Spread a breaking change over releases:

1. **Expand** — add the new field as optional (with a default). Bump the
   document's version (`schema_version: SchemaVersion = SchemaVersion("N+1")`
   on the model) and run `uv run python -m tests.storage.document_evolution.refresh`:
   it records the new shape and writes the golden fixture
   `tests/storage/golden/<collection>/v<N+1>.json`. The previous release
   ignores the new field; old rows read with the default.
2. **Backfill** — write the field for old rows: an upcaster (version N →
   N+1, a pure function of the stored JSON) fills it on read, and
   `workshop migrate-documents --collection <name>` rewrites the rows once
   the release is fully deployed.
3. **Require** — only in a later release, once no instance of the expand
   release or older is left and the backfill ran, make the field required.

Rules that follow from it:

- **Never rename or remove a field in one release.** Add the new name
  (expand), write both or upcast, switch the readers, and drop the old
  name in a later release with an upcaster that maps it.
- **Enum values:** a release may write a new value only if the release
  before it already knows the value. Add the value first (one release),
  write it in the next.
- **Types:** never change the type of a field in place (string → object,
  integer → string); add a new field instead. Lookup fields
  (`app/utilities/storage/document_lookup_fields.py`) have generated
  columns cast in SQL: a new type would make writes fail.
- **Required fields** start optional; a required field without a default
  needs an upcaster for old rows from the release that introduces it.
- **Nested objects** follow the same rules: their shapes are part of the
  document's snapshot.
- **Every shape change bumps the version.** The snapshot test
  (`tests/architecture_policy/test_document_evolution.py`) fails on a
  shape change without a bump or without a golden fixture of the new
  version; every golden fixture must still load, and after its upcasters
  nothing of the old shape may be left over.
- **Golden fixtures are history.** Never edit one; delete the fixtures of a
  version only together with its upcaster, after `migrate-documents` ran
  in every environment.

### `workshop migrate-documents`

```
workshop migrate-documents                    # every collection
workshop migrate-documents --collection bookings --batch 500
workshop migrate-documents --dry-run          # only count
```

Rewrites rows of older versions in the current shape, platform-wide (row
level security bypassed), in transactions of `--batch` rows. A row is
written only if nobody changed it since it was read, rows of the current
version are never touched, and rows of a newer version (a rollback in
progress) are left alone — running it again is harmless. It reports, per
collection, outdated, upgraded, newer, changed-meanwhile and failed rows
(with the first failing keys) and exits with 1 if any row failed.

Run it from the API's Render Shell or as a one-off job **after** the
release is fully deployed and you do not intend to roll back: the previous
release reads upgraded rows only if the change was purely additive. Never
run it in `preDeployCommand`.

## Changing the SQL schema

The same expand and contract, for tables and columns:

- Add tables, columns (nullable or with a default) and indexes; never drop
  or rename what the running release uses. Drop it in a later release.
- Migrations are forward-only and run in one transaction each
  (`migrations/README.md`); a rollback of the code does not roll back the
  schema, so the previous release must work with the new schema.
- Keep migrations short: they hold locks while both releases serve.

## Rollback

When the production smoke test fails, errors climb in Sentry, or owners
report a broken flow right after a deploy:

1. **Roll back all three services to the same commit.** Render → each of
   `workshop-api`, `workshop-worker`, `workshop-cabinet` → Events → the
   last good deploy → Rollback. API first, then worker, then cabinet.
2. **Stop the bad commit from coming back.** Move `release` to the good
   commit: `git push --force-with-lease origin <good-commit>:release`
   (the only force push ever made to `release`). Render then deploys that
   commit, so the services stay on it.
3. **Check.** Run the smoke workflow by hand (Actions → Deploy smoke test →
   Run workflow → production) and look at Sentry.
4. **Data.** Documents the bad release wrote stay and are read tolerantly
   by the good one (unknown fields ignored). Do not run
   `migrate-documents` until the fix is out. SQL migrations stay applied;
   if one must be undone, write a new migration.
5. **Fix forward** on `main`; staging and the smoke test promote the fix
   to `release` as usual.

Staging rolls back the same way (without step 2: it follows `main`).
