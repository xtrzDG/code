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
  `git push origin <commit>:release`. The promotion waits until
  production finished the post-deploy data tasks of the release it runs
  (`scripts/check_data_tasks.sh`, see "Data tasks after a deploy").
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
7. Set the repository variable `PRODUCTION_API_URL` (the production
   API's public address): the promotion reads production's `/readyz` and
   refuses while a data task is open. Without it every promotion stops
   with a message that names the variable.

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

The release with the admin's account actions and the client's story
(R13-ADMIN-ACTIONS, migration 1143, `SubscriptionDocument` and
`InvoiceDocument` version 3, `AuditLogEntryDocument` version 5) also
writes new enum values in the release that introduces them, an exception
to the enum rule below: six `AuditAction` values (`admin_trial_extended`,
`admin_discount_given`, `admin_credit_granted`, `admin_setup_fee_waived`,
`admin_invoice_marked_paid`, `admin_plan_overridden`). An old API instance
that lists an audit log holding such an entry may fail that page until the
overlap ends: nothing is lost. The timeline enums (`ClientTimelineKind`,
`ClientTimelineEvent`) are only answered by the API, never stored. The new
fields (a subscription's `discount` and `is_setup_fee_waived`, an
invoice's `discount_percent`, `discount_minor`, `credit_minor` and
`manual_payment`, an audit entry's `reason`) and the new collections
(`billing_credits`, `client_notes`, `client_health_changes`,
`admin_digest_states`) are unknown to the old release, which ignores them;
but an old worker that issues invoices during the overlap bills without
the discount and the credit, and an old instance that saves a subscription
(a renewal, a webhook) drops its discount and waiver: give them again
after the overlap (the audit log names them). Before rolling back past
that release, note that discounts, credit and waived fees stop applying.

The release with online-safe migrations (W12, migration 1122) added
trigger-filled lookup columns to `contacts`, `knowledge_items`, `bookings`
and `leads` that are empty for rows written before it. Since the data
tasks (below) their backfill runs by itself after every deploy; the old
manual `migrate-documents` and `backfill-lookup` steps are gone, and a
test (`tests/storage/test_data_tasks_on_postgres.py`) proves that such a
column fills and the lists that page by it come out complete.

The release with written booking confirmations (W16-BOOKING-CONFIRMATION,
`OutboundMessageDocument` version 6, no migration) also writes a new enum
value in the release that introduces it, an exception to the enum rule
below: the outbox kind `booking_confirmation`. An old worker that claims
the delivery job of such a row, or reads it among a guest's waiting
messages, fails the job, and the queue tries it again until a new worker
takes it: a confirmation is late during the overlap, not lost (it is
given up only past the booking's start). The website chat's confirmation
is a message of the conversation (`author: system`, `direction:
outbound`), which the old release stores and lists already but does not
show in the widget. Manage links (`/r/{token}`) are signed with a key
derived from `ENCRYPTION_KEY` and nothing is stored, so an old instance
answers their API with 404 during the overlap, and a rollback leaves the
links sent so far dead until the release is deployed again. Before
rolling back past that release, let the outbox drain (no `pending` rows of
the new kind).

The release with the spend guard (R12, migration 1142,
`AuditLogEntryDocument` version 5, `PlatformAlertStateDocument` version 3)
also writes new enum values in the release that introduces them, an
exception to the enum rule below: the audit action `spend_limit_reached`
(a business passed its hard daily spend limit) and the alert codes
`spend_spike` and `spend_budget`. An old API instance that lists an audit
log holding such an entry may fail that page, and an old alert job that
reads such an alert state fails that tick and runs again on the next,
both only during the overlap: nothing is lost. The new collections
(`business_limits`, `spend_limit_marks`) are unknown to the old release,
which ignores them: during the overlap an old instance answers model turns
and calls without the spend check and serves the website chat to any site.
The three new lookup columns of `usage_events` (`doc_kind`,
`doc_cost_micro_usd`, `doc_quantity`) are empty for rows written before
the migration, so the spend of a day that began before the deploy reads
low until the data task `backfill_lookup:usage_events.*` is done (a few
minutes after the deploy). A rollback needs nothing beyond the usual (the
old release ignores the new columns and collections).

The release with referrals and partners (R15, migration 1150,
`BusinessDocument` version 6, `BillingCreditDocument` version 2) also
writes a new enum value in the release that introduces it, an exception
to the enum rule below: the team role `agency` (an outside helper an owner
lets into the team, without billing). An old API instance reads a business
with such a member as invalid and fails that request, so add agency
members only once the deploy has finished; before rolling back past that
release, change every agency member to staff or remove them. The new
fields (a business's `referred_by` and `hides_powered_by`, a credit line's
`referral_of`) and the new collections (`partners`, `referral_codes`,
`referrals`, `commission_entries`) are unknown to the old release, which
ignores them; but during the overlap a business created on an old
instance is referred by nobody, a payment an old instance books earns no
commission and no month of credit (grant the month by hand: the referral
row names the business), and an old instance that saves a business drops
who referred it and a Plus owner's hidden "Powered by" link (choose it
again after the overlap).

The release with the subscription lifecycle (R14-SUB-LIFECYCLE,
migration 1161, `SubscriptionDocument` version 4, `BillingCreditDocument`
version 3) follows the enum rule below: it knows the subscription status
`paused` and the billing notices `pause_started` and `pause_ended`, but
`paused` sits behind the closed release gate `subscription_pause`, so no
pause is offered or stored even with `SUBSCRIPTION_PAUSE_ENABLED=true`.
The next release opens the gate; pausing then also needs the flag (default
`false`): turn it on once that release serves everywhere (an environment
change, a restart). Before rolling back past the release that opened the
gate, turn the flag off, let running pauses end or resume them in the
cabinet (no subscription with status `paused`), or the previous release
cannot read those subscriptions. The new fields (a subscription's
`pause_starts_at` and `pause_until`, a credit line's `save_offer_for`) and
the new collection `subscription_events` (cancellation reasons, offers,
pauses, win-back messages) are unknown to the old release, which ignores
them; but an old instance that saves a subscription during the overlap (a
renewal, a webhook) drops a pause scheduled just before (schedule it
again after the overlap), and an old instance that cancels records no
reason. The new periodic jobs `run_subscription_pauses` and
`send_win_back_messages` run only on new workers.

The release with the service levels (W15-METRICS, migration 1163,
`PlatformAlertStateDocument` version 4) also writes new enum values in the
release that introduces them, an exception to the enum rule below: the
alert codes `answer_budget_fast_burn`, `answer_budget_slow_burn`,
`api_budget_fast_burn` and `api_budget_slow_burn`. Only the
`platform_alerts` job writes them, each episode stored under its code, and
every reader asks for the codes it knows by key (the alerts job, the
system page, the status page), so an old instance never reads one. A
rollback leaves the four states unread; nothing needs cleaning. The new
collections (`service_level_slots`, `service_level_hours`) are unknown to
the old release, which ignores them; during the overlap an old API process
counts no requests for the availability SLI, so the hour of the deploy
reads a little low.

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
   N+1, a pure function of the stored JSON) fills it on read, and the
   collection's data task rewrites the rows once the release is fully
   deployed (`migrate_documents:<collection>`, "Data tasks after a
   deploy").
3. **Require** — only in a later release, once no instance of the expand
   release or older is left and the backfill ran, make the field required.

Rules that follow from it:

- **Never rename or remove a field in one release.** Add the new name
  (expand), write both or upcast, switch the readers, and drop the old
  name in a later release with an upcaster that maps it.
- **Enum values one release ahead:** a release may write a new value
  only if the release before it already reads it. Add the value behind a
  closed gate in `app/utilities/storage/release_gates.py` (storage refuses
  to write it; writers ask `is_gate_open`), open the gate in the next
  release, delete it in the one after.
  `tests/architecture_policy/test_enum_values_are_known_one_release_ahead.py`
  compares every stored enum with the snapshot of the last release
  (`tests/storage/release_enums.json`) and fails on a new value no closed
  gate covers; a field that is its document's key (alert codes) is exempt
  because a release reads only the keys it knows. When a release reaches
  production, record its snapshot:
  `uv run python -m tests.storage.document_evolution.record_release_enums
  $(git rev-parse origin/release) <release name>`.
- **Types:** never change the type of a field in place (string → object,
  integer → string); add a new field instead. Lookup fields
  (`app/utilities/storage/document_lookup_catalog.py`) have typed columns
  (generated up to 1114, trigger-filled from 1122): a new type would make
  writes fail.
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

The batch worker does this by itself after every deploy (see "Data tasks
after a deploy"); run it by hand from the API's Render Shell only to hurry
it, **after** the release is fully deployed and you do not intend to roll
back. Never run it in `preDeployCommand`.

## Data tasks after a deploy

What used to be manual steps after a deploy runs by itself: the
`data_tasks` registry (`app/registries/maintenance/data_task_registry.py`)
holds one task per collection whose documents have a version above 1 (the
`migrate-documents` rewrite to that version) and one per trigger-kept
lookup column added to a table that already held rows (the
`backfill-lookup` fill, declared in
`app/registries/maintenance/lookup_backfills.py`;
`tests/architecture_policy/test_lookup_columns_are_backfilled.py` fails
on an undeclared one). Their progress is stored in `data_task_states`
(migration 1164).

- **Who runs them.** The batch worker's job `run_data_tasks` (every 5
  minutes, one process at a time under an advisory lock) walks every open
  task in keyset batches of 5,000 rows, one short transaction per batch,
  and stores the position after each, so a restart goes on where it
  stopped. A run starts no batch after 4 minutes.
- **When.** Only once no worker of another release has beaten for 15
  minutes (`worker_heartbeats`): while the previous release still runs it
  would write the old shape again. After a rollback the same wait applies
  the other way round.
- **Failures.** A batch that fails as a whole is retried on the next run
  (the card shows the error). Rows a migration cannot upgrade leave the
  task `failed` with their keys; a new release walks it again, or a
  platform admin retries it (audited).
- **Where to look.** The admin system page's data-task card (progress
  against the table's estimated rows, failures, retry), `checks.data_tasks`
  of `GET /readyz` (open, failed and stalled counts; it never makes an
  instance not ready) and the alert `BACKFILL_STALLED` when a task is not
  done a day after it became due (runbook
  `docs/operations/runbooks/stalled-data-task.md`).
- **Lists.** The customer and knowledge lists say "still indexing" while
  a task that fills what they page by is open; they may miss older rows
  until it is done.
- **The next release waits.** The promotion to production
  (`.github/workflows/deploy-smoke.yml`) runs `scripts/check_data_tasks.sh` against
  production and refuses while any task is open, so a release that stops
  reading the old shape never lands before the rewrite finished. Re-run the
  promote job once the card shows every task done.

`workshop migrate-documents` and `workshop backfill-lookup` stay for a
manual run (they do the same work and are idempotent with the tasks).

## Changing the SQL schema

The same expand and contract, for tables and columns:

- Add tables, columns (nullable or with a default) and indexes; never drop
  or rename what the running release uses. Drop it in a later release.
- Migrations are forward-only and run in one transaction each, or
  statement by statement in a `-- workshop:no-transaction` file
  (`migrations/README.md`); a rollback of the code does not roll back the
  schema, so the previous release must work with the new schema.
- Migrations are online-safe: they run while the previous release writes,
  so nothing may hold a busy table for longer than a moment. No stored
  generated column, index built without `CONCURRENTLY`, unbatched
  `UPDATE`/`DELETE`, type change or validated constraint on an existing
  table (`tests/storage/test_migration_safety.py` lints every new file).
  A lookup field on an existing table is a nullable column filled by a
  BEFORE INSERT/UPDATE trigger, backfilled after the deploy by its data
  task (declare it in `app/registries/maintenance/lookup_backfills.py`),
  then indexed CONCURRENTLY in a later file.
- Every statement of `workshop migrate` waits at most 5 s for a lock and a
  file that timed out is tried again, five times in all, with growing
  jittered pauses. When the deploy still fails on it ("could not obtain
  lock"), something held the table: look for long transactions
  (`select pid, state, xact_start, query from pg_stat_activity where
  xact_start < now() - interval '1 minute'`), end them or wait for a
  quieter moment, and redeploy. Nothing of a failed file is recorded, and
  a half-built concurrent index is dropped and built again next time.

### `workshop backfill-lookup`

```
workshop backfill-lookup                                   # every column
workshop backfill-lookup --collection contacts --field last_seen_at --batch 5000
workshop backfill-lookup --dry-run                         # only count
```

Fills trigger-filled lookup columns of rows written before their
migration: platform-wide, in primary-key order, one short transaction per
batch (`--lock-timeout`, 5 s, and retries), only rows whose column is empty
and whose document holds the field. Idempotent and resumable; it prints,
per column, the rows it filled (with `--dry-run`, the rows left). Run it from the API's Render Shell or
as a one-off job **after** the deploy that added the columns, never in
`preDeployCommand`.

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
