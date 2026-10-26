# Go-live: what the owner creates, in order

The repository holds every reliability mechanism: deploys gated by CI, an
encrypted off-site backup and a weekly restore drill, alerts, a status page,
load tests and service levels. Each one proves something only once it runs
as a real service: deployed, backed up, restored on a clock, watched from
outside and sized on the tier production runs on. That needs accounts only
the owner can create. This page is the order to create them in, with a check
for every step; `docs/LAUNCH.md` (in Russian) covers each external account
in detail, and its section 8 summarises this page.

Conventions:

- `<angle brackets>` are values you have and the repository never holds
  (addresses, ids, keys). Never commit them.
- Every capitalised name with underscores on this page (`SENTRY_DSN`) is
  an environment variable, a GitHub secret or variable, or an option of a
  load test.
  `tests/platform/test_go_live_checklist.py` fails when one is read by
  nothing, when the backend reads it and `.env.example` does not list it
  (`web/.env.example` for the cabinet), and when a workflow reads a secret
  or variable this page does not name.
- Commands run from a clone of the repository, with `gh` signed in as a
  repository administrator.
- Keep the evidence of each check (a run, a log line, a screenshot) for the
  pull request or issue that closes `docs/PLAN.md` item 17.22.3.

## Where things stand (2026-10-26)

What GitHub showed on that day, and why the steps come in this order:

- **The default branch is not `main`.** Work happens on a long-running
  branch that is the repository's default; `main` is still the first
  commit (an ancestor of that branch, so it can fast-forward), unprotected,
  and `release` does not exist. Everything else assumes `main`: CI's push
  trigger, the signed images (`refs/heads/main`), staging
  (`branch: main` in `render.staging.yaml`), the promotion to `release`,
  and the branch protection `.github/repository-settings.json` expects.
  Scheduled workflows run on the default branch.
- **Scheduled workflows fire**, from the default branch, late: in October
  2026 GitHub started them between about 4 and 9½ hours after their cron
  time (the 02:23 UTC runs between 07:00 and 09:40). Never rely on a
  scheduled run's hour; `schedule-watch.yml` allows 8 days.

| Workflow | Cron (UTC) | Scheduled runs | What it still needs |
| --- | --- | --- | --- |
| `restore-drill.yml` | `23 2 * * *`, `41 3 * * 1` | the nightly round trip green every day since 2026-10-04 (run 40288959906); the Monday production job is skipped (run 40298721869) | step 6: `BACKUP_S3_BUCKET` and the `backup-drill` environment |
| `perf.yml` | `17 4 * * 1` | green on 2026-10-26 (run 40304785133) after red runs on 10-05, 10-12 and 10-19 | step 10: the tier, and the baseline |
| `evals-nightly.yml` | `23 2 * * *` | green every night (run 40288729650), but the benchmark is skipped | step 5: `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` |
| `contracts-live.yml` | `47 3 * * *` | runs every night; the drift job is red whenever a vendor changed a specification (the "Provider drift" issue); the sandbox calls skip every provider without its secret | step 5: the sandbox secrets |
| `codeql.yml` | `17 4 * * 1` | green (run 40305466632) | nothing |
| `repo-settings.yml` | `23 5 * * *` | red every day since it was added (run 40313271467: the secret is not set) | step 1: `REPO_SETTINGS_TOKEN` and the branch protection |
| `zap.yml` | `41 3 * * 2` | none yet: added on 2026-10-23, first Tuesday 2026-10-27 | nothing |
| `schedule-watch.yml` | `37 6 * * *` | green every day (run 40330863312); it holds issues open for `repo-settings.yml` and `perf.yml` | close the `perf.yml` issue with run 40304785133 |
| `major-updates.yml` | `23 7 1 1,4,7,10 *` | none yet: added on 2026-10-06, first run 2027-01-01 | nothing |

Check again at any time:
`gh run list --event schedule --limit 30 --json workflowName,headBranch,conclusion,createdAt`.

## 1. `main` as the default branch, protected, and the `release` branch

1. Bring `main` up to the working branch: merge the working branch's pull
   request into `main`, or, while `main` is unprotected, fast-forward it:
   `git push origin <working-branch>:main`.
2. GitHub → Settings → General → Default branch → `main`. Scheduled
   workflows, Dependabot and new pull requests follow it from then on; keep
   working in pull requests into `main`.
3. Protect `main` as `.github/repository-settings.json` says (SECURITY.md,
   "Repository settings"): pull requests only; the required checks
   `CI passed (every gate)`, `Analyze (python)`,
   `Analyze (javascript-typescript)` and `OpenAPI breaking changes (oasdiff)`;
   no force push; no deletion. Turn on private vulnerability reporting and
   Dependabot security updates.
4. Add the repository secret `REPO_SETTINGS_TOKEN`: a fine-grained token of
   this repository only with "Administration: Read-only". Put its expiry
   date in the team calendar.
5. Create `release` from `main`: `git push origin main:release`. If you
   protect `release` as well, allow GitHub Actions to push to it (the
   promotion fast-forwards it; `docs/operations/deploys.md`, "One-time
   setup").

Check:

```bash
gh repo view --json defaultBranchRef --jq .defaultBranchRef.name   # main
git ls-remote --heads origin main release                          # both
gh workflow run repo-settings.yml
gh run list --workflow repo-settings.yml --limit 1                 # completed, success
```

The next morning `gh run list --event schedule --limit 10 --json
workflowName,headBranch` names `main`, and the CI run of the push to `main`
has a green `publish-images` job. Close the issue "Schedule watch:
repo-settings.yml has no successful run in 8 days" with the green run.

## 2. Staging on Render (`render.staging.yaml`)

1. Render → New → Blueprint → this repository, Blueprint path
   `render.staging.yaml`: `workshop-staging-db` (`basic-256mb`) and the API,
   worker and cabinet on `starter`, all in Frankfurt, all following `main`.
   The env group `workshop-staging` sets `APP_ENV` to `production` and
   `LLM_PROVIDER` to `scripted`, and generates its own `ENCRYPTION_KEY`.
2. Fill in what the Blueprint asks for. `workshop-staging-api`:
   `APP_BASE_URL`, `CABINET_BASE_URL`, `CORS_ALLOWED_ORIGINS`,
   `PLATFORM_ADMIN_EMAILS`, the e-mail sign-in (`SMTP_HOST`, `SMTP_PORT`,
   `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`) and
   `SENTRY_DSN` (step 7). `workshop-staging-cabinet`: `BACKEND_URL` (the
   API's internal address with `http://` and port 8000),
   `SECURITY_CONTACT_EMAIL` and `SENTRY_DSN`. Never production's keys.
3. The first deploy of the API and the worker stops with "Production
   connects with two roles": create the roles (step 3), set
   `DATABASE_URL_TENANT` and `DATABASE_URL_PLATFORM` on
   `workshop-staging-api` (the worker copies them) and deploy again.
4. In staging's cabinet create the smoke business: the website chat turned
   on and a live assistant (`docs/operations/deploys.md`, "One-time setup",
   step 3). Note its id.

Check:

```bash
curl -fsS <staging-api-url>/readyz                                  # "status": "ready"
SMOKE_WIDGET_BUSINESS_ID=<smoke-business-id> SMOKE_EXPECT_REPLY="staging server" \
  scripts/smoke.sh <staging-api-url> <staging-cabinet-url>          # every check passes
```

## 3. Database roles and pgvector (once per database server)

Since migration 1200 (`migrations/1200_tenant_and_platform_roles.sql`) the
API and the workers log in with two roles of their own: `workshop_tenant_app`
(member of `workshop_tenant`, sees one business) and `workshop_platform_app`
(member of `workshop_platform`, sees every row). The database's own user
(`workshop` in both Blueprints) stays the migration role and joins
`workshop_platform`. Run the SQL of `docs/operations/deploys.md`, "Setting
the roles up (once per database server)", on staging's and on production's
server (Render → the database → Connect → External), each with its own
passwords. Then set `DATABASE_URL_TENANT` and `DATABASE_URL_PLATFORM` on the
environment's API: the internal address of the database with the login
role and its password.

The knowledge embeddings (migration `migrations/1211_knowledge_embeddings.sql`)
need pgvector. As the migration role run
`select workshop.enable_knowledge_embeddings();`; when it returns `f`, an
administrator runs `create extension vector;` first, then the function again
(docs/LAUNCH.md, section 4.2). From then on every backup holds the
extension, and the restore drill restores into Postgres with pgvector.

Check, with `psql "<external-connection-string>"`:

```sql
select r.rolname, r.rolcanlogin, r.rolsuper, r.rolbypassrls,
       array(select g.rolname from pg_auth_members m
             join pg_roles g on g.oid = m.roleid
             where m.member = r.oid) as member_of
  from pg_roles r
 where r.rolname like 'workshop%'
 order by 1;
-- no row has rolsuper or rolbypassrls; workshop_tenant_app is a member of
-- workshop_tenant only, workshop_platform_app of workshop_platform, and the
-- migration role (workshop) of workshop_platform.
select extversion from pg_extension where extname = 'vector';   -- a version
select workshop.enable_knowledge_embeddings();                  -- t (idempotent)
```

`GET /readyz` answers `ready` only while both pools answer, and the API
refuses to start with a role that is a superuser, may bypass row-level
security or sits in the wrong group.

## 4. Production on Render (`render.yaml`)

1. With `release` in place (step 1) and the accounts of docs/LAUNCH.md,
   section 4: Render → New → Blueprint → `render.yaml`. It creates
   `workshop-db` (`pro-8gb`), `workshop-api` (2 × `starter`),
   `workshop-worker` (2 × `starter`), `workshop-batch-worker` (`standard`),
   the cron `workshop-backup` (01:17 UTC) and `workshop-cabinet`
   (`starter`), all in Frankfurt, all following `release`.
2. Roles and pgvector on `workshop-db` (step 3), then
   `DATABASE_URL_TENANT` and `DATABASE_URL_PLATFORM` on `workshop-api`.
3. The addresses and the rest of the first setup: docs/LAUNCH.md,
   section 3, step 5 (`APP_BASE_URL`, `CABINET_BASE_URL`,
   `CORS_ALLOWED_ORIGINS` on the API; `BACKEND_URL`, `SITE_URL`,
   `SECURITY_CONTACT_EMAIL` and `SENTRY_DSN` on the cabinet).
4. Wave 21's variables, on `workshop-api` (both workers copy each one by
   name); leave empty what you do not use yet:

| Feature | Variables | Before you set them |
| --- | --- | --- |
| Knowledge search by meaning | `EMBEDDINGS_API_KEY`; optionally `EMBEDDINGS_MODEL_ID` in the env group `workshop-backend` | pgvector (step 3). Leave the key empty until 2026-11-22: before then production refuses to start with it (the sub-processor notice, docs/LAUNCH.md 4.2) |
| WhatsApp Embedded Signup, Instagram, Messenger | `META_APP_ID`, `META_APP_SECRET`, `META_VERIFY_TOKEN`, `META_EMBEDDED_SIGNUP_CONFIG_ID` | docs/LAUNCH.md 4.5; the webhook is `<production-api-url>/v1/channels/meta/webhook` |
| SMS sign-in codes and phone numbers in the cabinet | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_MESSAGING_SERVICE_SID`, `PHONE_NUMBER_PROVIDER` (`twilio`); optionally `PHONE_NUMBER_PRICE_MARKUP_PERCENT` in `workshop-backend` | docs/LAUNCH.md 4.3 and 4.6 |
| Card payments in the EU, the US and Israel | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | docs/LAUNCH.md 4.7.2; the webhook is `<production-api-url>/v1/payments/stripe/webhook`; owners pay through Flitt until a later release opens the gate `stripe_payments`, not before 2026-11-22 |

Check:

```bash
curl -fsS <production-api-url>/readyz                                # "status": "ready"
scripts/smoke.sh <production-api-url> <production-cabinet-url>       # every check passes
curl -fsS "<production-api-url>/v1/auth/login-options?country_code=<your-country-code>"
```

Then the walk-through of docs/LAUNCH.md, section 7. In Render the
Environment tab of `workshop-worker` and `workshop-batch-worker` shows each
wave 21 variable linked to `workshop-api`, and Meta's webhook form accepts
the address with `META_VERIFY_TOKEN` ("Verify and save").

## 5. GitHub environments, variables and secrets

Every secret and variable the workflows read. Settings → Environments for
the three environments, Settings → Secrets and variables → Actions for the
rest. Names only: the values are yours.

| Where | Variables | Secrets | Read by |
| --- | --- | --- | --- |
| environment `staging` | `API_URL`, `CABINET_URL`, `SMOKE_WIDGET_BUSINESS_ID` (step 2), `SMOKE_EXPECT_REPLY` (`staging server`) | none | `deploy-smoke.yml` |
| environment `production` | `API_URL`, `CABINET_URL` (no smoke business unless one real model answer per deploy is wanted) | none | `deploy-smoke.yml` |
| environment `backup-drill` | none | `BACKUP_S3_ACCESS_KEY_ID` and `BACKUP_S3_SECRET_ACCESS_KEY` (the drill's read-only key), `BACKUP_AGE_IDENTITY` (the drill's private age key), `SENTRY_DSN` (the backend project) | `restore-drill.yml`, production job |
| repository | `PRODUCTION_API_URL` (the promotion waits for production's data tasks); `PROMOTE_AFTER_STAGING_SMOKE` (optional: `false` promotes by hand) | none | `deploy-smoke.yml` |
| repository | `BACKUP_S3_ENDPOINT_URL`, `BACKUP_S3_REGION`, `BACKUP_S3_BUCKET`, `BACKUP_S3_PREFIX` (optional, `workshop/` by default) | none | `restore-drill.yml`: the Monday drill runs only once `BACKUP_S3_BUCKET` is set |
| repository | `SENTRY_ORG`, `SENTRY_PROJECT` (step 7) | `SENTRY_AUTH_TOKEN` (step 7) | `ci.yml`, the cabinet's source maps |
| repository | `LEGAL_TEXTS_FINAL` (`true` once the lawyer approved the legal texts, docs/legal/README.md) | none | `ci.yml` |
| repository | none | `REPO_SETTINGS_TOKEN` (step 1) | `repo-settings.yml` |
| repository | none | `OPENAI_API_KEY`, `OPENAI_PROJECT_ID`, `ANTHROPIC_API_KEY`: without both keys the benchmark is skipped and the run is still green (evals/README.md) | `evals-nightly.yml` |
| repository | none | sandbox credentials only (tests/contracts/README.md): `CONTRACTS_TELEGRAM_BOT_TOKEN`, `CONTRACTS_META_ACCESS_TOKEN`, `CONTRACTS_META_PHONE_NUMBER_ID`, `CONTRACTS_META_TEST_RECIPIENT`, `CONTRACTS_TWILIO_TEST_ACCOUNT_SID`, `CONTRACTS_TWILIO_TEST_AUTH_TOKEN`, `CONTRACTS_GOOGLE_CLIENT_ID`, `CONTRACTS_GOOGLE_CLIENT_SECRET`, `CONTRACTS_GOOGLE_REFRESH_TOKEN`, `CONTRACTS_OPENAI_API_KEY`, `CONTRACTS_ANTHROPIC_API_KEY`, `CONTRACTS_ELEVENLABS_API_KEY` | `contracts-live.yml`, the sandbox calls |

Render reports each deploy to GitHub as a deployment named after the
service, which starts the smoke test (`docs/operations/deploys.md`,
"One-time setup", step 5).

Check:

```bash
gh api 'repos/{owner}/{repo}/environments' --jq '.environments[].name'   # backup-drill, production, staging
gh variable list --env staging
gh variable list --env production
gh secret list --env backup-drill
gh variable list
gh secret list
gh workflow run deploy-smoke.yml -f environment=staging
```

The staging run is green in all three jobs (smoke test, signed images,
promotion to `release`); the signed-images job needs the CI run of that
commit on `main` (step 1). The next nightly `evals-nightly.yml` run plays
the datasets instead of skipping them, and `contracts-live.yml` lists
fewer skipped providers (`-rs` in its log).

## 6. Backups: the EU bucket, the age keys and the first drill

The reference is `docs/operations/backup-restore.md` ("The bucket", "Keys
and custody"); docs/LAUNCH.md 4.11 says the same in Russian.

1. A private bucket in the EU at another provider than Render, versioning
   on, a lifecycle rule that expires noncurrent versions after 14 days and
   aborts incomplete multipart uploads after 2 days.
2. Three access keys: the backup cron's (put, list and delete under
   `workshop/`), the drill's (get and list only) and the deletion ledger's
   (put, get and list under `workshop/deletion-ledger/` only, no delete).
3. Two age identities, made on an operator's machine, never on a server:

   ```bash
   age-keygen -o drill.txt  && age-keygen -y drill.txt    # prints the drill's public key
   age-keygen -o escrow.txt && age-keygen -y escrow.txt   # prints the escrow public key
   ```

   The drill's private key becomes the secret `BACKUP_AGE_IDENTITY` of
   `backup-drill`. The escrow key is printed, sealed in the company safe and
   copied into the founders' password manager; two named people can reach
   it. Then delete both files from the machine.
4. Render, `workshop-backup`: `BACKUP_S3_ENDPOINT_URL`, `BACKUP_S3_REGION`,
   `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY_ID` and
   `BACKUP_S3_SECRET_ACCESS_KEY` (the cron's key), and
   `BACKUP_AGE_PUBLIC_KEY` = `<drill-public-key>,<escrow-public-key>`.
   `workshop-batch-worker`: the same bucket and public keys with the
   ledger's key. Retention (`BACKUP_KEEP_DAILY`, `BACKUP_KEEP_MONTHLY`)
   and the overdue mark (`BACKUP_MAX_AGE_HOURS`) have defaults.
5. GitHub: the repository variables and the `backup-drill` secrets of
   step 5.

Check:

1. Render → `workshop-backup` → Trigger Run. Its log names the archive
   (`workshop/<year>/<month>/<time>Z.pgdump.age`) and its manifest;
   `/admin/system` shows the backup; Sentry Crons shows an OK check-in of
   `database-backup`.
2. `gh workflow run restore-drill.yml -f production=true`: the job
   "Restore production's newest backup" is green and Sentry Crons shows an
   OK check-in of `restore-drill`. From then on it runs every Monday.
3. Once, the escrow holders prove their key opens a backup, on a trusted
   machine with the drill's bucket key in an AWS CLI profile and
   `pg_restore` 17 or newer:

   ```bash
   aws s3 cp --profile <drill-profile> --endpoint-url <s3-endpoint-url> \
     s3://<backup-bucket>/workshop/<year>/<month>/<archive>.pgdump.age .
   age --decrypt --identity <escrow-key-file> <archive>.pgdump.age \
     | pg_restore --list > /dev/null && echo "the escrow key opens it"
   ```

4. Once a quarter, time a full restore from the off-site backup
   (`docs/operations/backup-restore.md`, "Rehearsing the runbook") and
   write the measured RTO into that page.

## 7. Sentry

1. sentry.io in the EU region: a project for the backend (API, workers,
   the backup cron and the restore drill) and one for the cabinet. Staging
   gets projects of its own: it runs with `APP_ENV` `production` as well,
   so its events would look like production's.
2. `SENTRY_DSN` of the backend project on `workshop-api`;
   `workshop-worker`, `workshop-batch-worker` and `workshop-backup` copy
   it. `SENTRY_DSN` of the cabinet project on `workshop-cabinet`. The same
   on `workshop-staging-api` and `workshop-staging-cabinet` with staging's
   projects, and the backend DSN as the `backup-drill` secret.
3. Readable cabinet stack traces: the repository secret
   `SENTRY_AUTH_TOKEN` (an organization token that may upload releases)
   and the repository variables `SENTRY_ORG` and `SENTRY_PROJECT` (the
   cabinet's project). CI uploads the source maps on every push to `main`.
   Render builds the cabinet's image itself without the token, so
   production's traces stay minified until that build gets the same three
   values (`docs/operations/observability.md`, "Cabinet source maps").
4. The periodic jobs create their Crons monitors at their first check-in:
   `platform-alerts` (every five minutes, the customer worker),
   `database-backup` (daily), `restore-drill` (weekly) and the batch
   worker's jobs, such as `run-data-tasks`. Point each monitor's alert at
   the on-call person (step 9).

Check:

```bash
# Render → workshop-api → Shell (then the same in workshop-worker's Shell)
python -c "import os, sentry_sdk; sentry_sdk.init(os.environ['SENTRY_DSN']); sentry_sdk.capture_message('go-live check'); sentry_sdk.flush()"
```

The message appears in the backend project within a minute. In the
cabinet, signed in, run `setTimeout(() => { throw new Error("go-live check"); });`
in the browser's console: the error appears in the cabinet's project. Crons
shows `platform-alerts` checking in every five minutes. After the next push
to `main`, CI's step "Upload the cabinet's source maps to Sentry" does not
say "No SENTRY_AUTH_TOKEN secret", and Sentry's release of that commit has
its source maps.

## 8. An external uptime monitor in the EU

The platform cannot report its own death: an uptime service with an EU
probe location (UptimeRobot, Better Stack) checks it from outside
(`docs/operations/slo.md`, "What the job cannot see";
`docs/operations/status-page.md`). Every check once a minute, without a
token, alerting after two failures:

| Check | Address | Up when |
| --- | --- | --- |
| API readiness | `<production-api-url>/readyz` | 200: this instance and the database answer |
| Customer pipeline | `<production-api-url>/healthz/pipeline` | 200; 503 means no worker pulsed for 5 minutes or a customer message waited over 120 s |
| Status page | `<production-cabinet-url>/status` | 200: the cabinet serves the page owners read during an incident |

Add the same pipeline check for staging, `<staging-api-url>/healthz/pipeline`,
for the drill below. Link the monitor's public page from the status page's
footer once it exists.

Check: all three are up for a day. Then the drill: Render →
`workshop-staging-worker` → Suspend. Within about seven minutes (five
without a pulse, two failed checks) staging's pipeline check is down and
the on-call person is paged (step 9). Resume the worker; the check
recovers.

## 9. A paging rota

Who answers what, and how fast, is in `docs/operations/incident.md`:
SEV1 at once, day or night; SEV2 within 30 minutes from 08:00 to 23:00
Tbilisi time.

1. A weekly rota of a primary and a secondary, among the people who may
   roll back, restore and rotate keys. Keep it, with the phone numbers, in
   the paging or uptime service, not in this repository.
2. Route every source to the rota:
   - the uptime monitor (step 8): a phone call or push to the primary, the
     secondary when the primary does not acknowledge;
   - Sentry (step 7): the Crons monitors and new production issues;
   - the platform alerts: the ops Telegram group in
     `PLATFORM_ALERT_TELEGRAM_CHAT_IDS` (sent by the bot of
     `TELEGRAM_PLATFORM_BOT_TOKEN`) and the addresses in
     `PLATFORM_ALERT_EMAILS` (sent through the SMTP settings), on
     `workshop-api`: the workers copy them, and the API's pipeline
     watchdog sends `worker_down` with them when no worker runs
     (docs/LAUNCH.md 4.9);
   - GitHub: the rota watches the repository's issues, where
     `schedule-watch.yml` and `contracts-live.yml` report.
3. A handover each week: the open alerts, issues and the error budget
   (`/admin/system`).

Check: a test notification of the paging service reaches the primary's
phone, and the secondary's when it is not acknowledged; the staging drill
of step 8 pages the person on call; the ops group received at least one
`FIRING` and `RESOLVED` pair (the drill's `worker_down`, when staging's
env group has the same alert settings).

## 10. Capacity on the target tier

`perf.yml` measures on GitHub's runner: four vCPU, four API processes in one
container. Production runs `starter` instances, half a CPU and 512 MB each:
two API instances of one process, two customer workers, and the batch
worker on `standard` (`docs/operations/capacity.md`, "What one process
carries", "Worker roles").

**The baseline.** Run the weekly job by hand and accept its numbers:

```bash
gh workflow run perf.yml -f scale=full -f update_baseline=true -f load_test=true
gh run download <run-id> --name perf-report --dir <download-dir>
```

Copy the artifact's `baseline.json` over `perf/baseline.json` and commit it
in a pull request that names the run (`docs/operations/capacity.md`, "The
baseline").

**The tier.** The k6 scenarios play many client networks through a
forwarded address that only the load stack trusts
(`perf/docker-compose.perf.yml`), so never point them at staging or
production. Hold the load stack's API and worker to one `starter` instance
each and give them half of the weekly load, the share of one of
production's two instances:

```bash
TIER="$(mktemp -d)/tier.yml"
cat > "$TIER" <<'YAML'
services:
  api:
    environment:
      WEB_CONCURRENCY: "1"
    cpus: 0.5
    mem_limit: 512m
  worker:
    cpus: 0.5
    mem_limit: 512m
YAML
C="docker compose -f docker-compose.yml -f perf/docker-compose.perf.yml -f $TIER"
$C up --detach --build --wait api
$C up --detach worker
$C run --rm -T api seed-load --businesses 50 --messages 200000 \
    --bookings 20000 --visitors 1000 --manifest - > perf/manifest.json
perf/wait-for-drain.sh "before cabinet browsing"
$C --profile load run --rm k6 run -e CABINET_USERS=50 /perf/k6/cabinet_browsing.js
perf/wait-for-drain.sh "before widget polling"
$C --profile load run --rm k6 run -e WIDGET_VISITORS=500 /perf/k6/widget_polling.js
perf/wait-for-drain.sh "before the webhook burst"
$C --profile load run --rm k6 run -e WEBHOOK_RATE=100 /perf/k6/webhook_burst.js
$C down --volumes
```

During each scenario, `docker stats --no-stream $($C ps -q api worker)` in
a second terminal records CPU and memory. When a threshold fails, lower the
load until it passes: that load times the instance count is what
production carries. Write the figures, the date and the commit into
`docs/operations/capacity.md`, next to the runs already there, in a pull
request.

**Render itself.** During the pilot, read the Metrics tab of `workshop-api`
and `workshop-worker` at the busiest hour: CPU and memory against the tier,
with the limits measured above. Memory near 512 MB is the first sign;
`MEDIA_MAX_CONCURRENT_UPLOADS` was sized for it without a measurement.

Check: the baseline pull request is merged and the next Monday's scheduled
`perf.yml` run compares green against it; `docs/operations/capacity.md`
holds the tier's figures.

## 11. Two weeks of pilot data, then the alert thresholds

The objectives and thresholds of `docs/operations/slo.md` are reasoned, not
measured. After at least 14 days of pilot traffic:

1. Read the error budget of each objective on `/admin/system`
   (`GET /v1/admin/system/error-budget`): answered within 60 s, the answer
   p95 against 15 s, API availability, and the uptime monitor's
   availability next to it.
2. List every alert that fired (the ops group's `FIRING` and `RESOLVED`
   messages) and mark each as a real problem or noise; list the problems
   owners reported that no alert caught.
3. Change a rule that paged without a real problem twice, or missed one,
   in `ops/alerts/` and `app/use_cases/admin/alerts/alert_rules.py` in the
   same pull request, with the two weeks' figures in its description
   (`docs/operations/slo.md`, "Changing a rule";
   `tests/platform_ops/test_alert_rules_as_code.py` keeps both equal).
   An objective itself changes only with the founder (the error budget
   policy).

Check: the pull request is merged, and the following two weeks page only
for real problems.
