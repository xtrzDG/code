# Security policy

Assistant Workshop answers customers of small businesses and stores their
conversations, contacts, bookings and call recordings. We treat every report
about the safety of that data as urgent.

## Reporting a vulnerability

- **Use GitHub's private vulnerability reporting**: the repository's
  *Security* tab, then *Report a vulnerability*. Only the maintainers see
  the report, and we can discuss and fix it in a private fork. (Maintainers:
  keep *Settings > Code security > Private vulnerability reporting*
  switched on.)
- Or write to the security mailbox named first in the cabinet's
  `/.well-known/security.txt`.
- Do **not** open a public issue, pull request or discussion about it.
- Include what you found, where (route, page, file), how to reproduce it,
  what an attacker gains, and any proof of concept. Use test accounts and
  your own data only.

The cabinet publishes these contacts as `/.well-known/security.txt`
(RFC 9116, `web/src/server/securityTxt.ts`): the platform's security
mailbox first (`SECURITY_CONTACT_EMAIL`), then GitHub's private reporting,
this policy on `main` and the file's own `Canonical` address (`SITE_URL`).
A test fails 30 days before its `Expires`, so it is renewed in time, and
the deploy smoke test (`scripts/smoke.sh`) fails when a deployed cabinet
names no mailbox or no https canonical address. The trust boundaries, the
STRIDE threats and the code and tests behind each mitigation are in
[docs/security/threat-model.md](docs/security/threat-model.md); who has
access to what is reviewed every quarter
([docs/security/access-review.md](docs/security/access-review.md)).

## Scope

In scope:

- the HTTP API (`/v1/...`) and its webhooks (Telegram, Meta, Stripe,
  Flitt, ElevenLabs, Zadarma, Twilio, the Google Calendar callback);
- the website widget (`/widget.js`, `/v1/widget/...`), the hosted chat
  page (`/c/...`) and the guest's booking page (`/r/...`);
- the owner cabinet (`web/`) and its server routes (`/api/backend/*`);
- the background worker, the migration runner and the Docker images built
  from this repository;
- this repository's CI configuration and supply chain.

Out of scope: the platforms we integrate with (report to Telegram, Meta,
Flitt, ElevenLabs, OpenAI, Anthropic or Google directly), volumetric denial
of service, social engineering of staff, attacks that need a compromised
device or browser, self-XSS, and reports from automated scanners without a
demonstrated impact.

## What happens next (triage SLA)

| Step | Target |
| --- | --- |
| Acknowledge the report | 2 business days |
| Assess severity (CVSS 4.0) and confirm or reject | 5 business days |
| Fix released: Critical | 7 days |
| Fix released: High | 30 days |
| Fix released: Medium | 90 days |
| Fix released: Low | next planned release |
| Notify affected clients of a personal-data breach | within 48 hours of becoming aware (DPA 12.1) |

We keep the reporter informed at each step, credit them in the release
notes if they wish, and do not pursue good-faith research that follows this
policy: no access to other people's data beyond what proves the issue, no
destruction or degradation of service, and reasonable time for us to fix
before disclosure.

## How the code is protected

Every pull request and every push to `main` runs (`.github/workflows/`):

| Gate | Tool | Fails on |
| --- | --- | --- |
| Python dependencies | `pip-audit --strict` on the locked set (`uv export`), pip-audit itself hash-pinned | any known vulnerability |
| Cabinet dependencies | `npm audit --audit-level=high`, runtime and dev packages | high or critical |
| Secrets in the whole history | `gitleaks` | any secret not reviewed in `.gitleaksignore` |
| Python static analysis | `bandit` with `bandit-baseline.json` | any finding not in the dated baseline |
| Semantic analysis | CodeQL (Python, JavaScript/TypeScript and the workflows themselves, `actions`; `security-extended`) | new high-severity alerts |
| Workflows | `Workflow audit (actionlint, zizmor)`: syntax, shellcheck, template injection, credentials left in checkouts, dangerous triggers, unpinned or impostor actions, permissions | any finding not commented where it occurs |
| Container images | Trivy on the backend and cabinet images with its vulnerability, misconfiguration and secret scanners (`.github/trivy-secret.yaml` exempts only third-party package folders) | HIGH or CRITICAL: a vulnerability with a fix available, a misconfiguration or a secret |
| Software bill of materials | syft (CycloneDX JSON per image, kept 30 days as a CI artifact and, on `main`, attested to each published image) | — |
| New dependencies | `actions/dependency-review-action` on pull requests with `.github/dependency-review-config.yml` (its summary also a comment on the pull request) | a new dependency with a high vulnerability, or a denied licence (AGPL, GPL, SSPL, BUSL, CC-BY-NC) without a reviewed exception |
| New dependencies on their registries | `scripts/dependency_registry_review.py` on pull requests: each new direct dependency of the cabinet, the Zapier app, the Lighthouse tool and `pyproject.toml` measured on npm or PyPI (age, publishers, deprecation, install-time code, licence, source, lookalike names) | a name the registry does not know, a deprecated, archived, quarantined or wholly yanked package, one first released under 30 days ago, a lookalike of a popular or already used name, or one installed from outside the registry (`not-from-registry`), unless `.github/dependency-registry-review.toml` accepts it with a reason; a registry that does not answer |
| Secrets in the cabinet build | `web/scripts/scan-bundle-secrets.mjs` right after `next build` (`web-build`) | a provider key shape in `.next/static` or `.next/server`, or the value of a secret variable of `web/.env.example` or `.env.example` in what browsers receive when the build's environment holds one (CI's build holds none, so there only the key shapes are checked); no exception list |
| Payment pages' scripts | `web/scripts/payment-page-integrity.mjs` in `web-build` against `web/payment-page-scripts.json` (SHA-384 of every first-party script of the billing page and the hosted chat page) | a build it cannot read; a changed script is a warning with the table, and the pull request updates the inventory |
| The assistant's recorded answers | `Evals replay gate` (`evals`): when a change touches what the model sees, every recorded conversation replayed offline without keys | a stale cassette, a failing scenario or any hallucination (`--min-pass-rate 1 --max-hallucination-rate 0`) |
| API contract | `oasdiff breaking` against the merge base | breaking changes without the `api-breaking` label |
| API fuzzing | `Backend tests (api-fuzz 1/1)`: hypothesis over every documented operation, signed in, and hostile bodies (`tests/api_fuzz`) | any server error other than an unavailable provider |
| Action and image pinning | `tests/platform/test_ci_workflows.py`, `tests/platform/test_image_pins.py` | an action not pinned to a commit SHA, an image without its digest |

A pull request that touches a security boundary (sign-in, keys,
payments, webhooks, tenant isolation, the assistant's tools, CI) gets the
label `risk:high` from `.github/workflows/risk-labels.yml`
(`.github/labeler.yml`) and the differential review of
`docs/security/change-risk.md`.

On a schedule, so that what was safe yesterday is checked again today
(`schedule-watch.yml` opens an issue when one has not succeeded for 8 days):

| When | Workflow | What |
| --- | --- | --- |
| nightly | `dependency-audit.yml` | `uv.lock`, `web/` and the Zapier app's lockfile (runtime and dev, every severity) against today's advisories; the issue "Dependency advisories" lists each with its remediation deadline (below) and the run fails while a critical or high one is past it |
| weekly | `image-rescan.yml` | the images of what production runs (`release`) rebuilt from their pinned bases and scanned again with today's Trivy database; an image base or release older than 90 days fails |
| weekly | `zap-staging.yml` | the active scan of staging (below) |
| hourly | `synthetics.yml` | production as customers meet it: health, a widget chat round trip, and a booking made and cancelled through the public API |
| daily | `repo-settings.yml` | the repository settings below |
| weekly | `payment-page-integrity.yml` | the payment pages' scripts (billing page, hosted chat page) against their reviewed SHA-384 inventory: with `PRODUCTION_CABINET_URL`, as production serves them against the `release` branch's inventory, otherwise a fresh build of `main` (the variable and the `release` branch are owner steps, `docs/operations/go-live.md`); no secrets, the check reads only, and only its issue step may write issues; a difference fails the run and opens the issue "Payment page scripts changed" (PCI DSS 6.4.3 and 11.6.1 intent) |
| nightly | `evals-nightly.yml` | the assistant against the real models (with `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`; without both the run is skipped with a notice, which is the case until the owner sets them): pass rate at least 85 % and hallucination rate at most 2 % (its inputs `min_pass_rate`, `max_hallucination_rate`) |

### Signed images and build provenance

On every commit of `main` (a push, or the CI run `automerge.yml` starts
after it merged a Dependabot group, since that merge pushes no event),
after every gate passed, CI publishes the backend
and cabinet images it built and scanned to ghcr.io under the commit SHA,
attaches SLSA build provenance (`actions/attest-build-provenance`) and the
CycloneDX SBOM as an attestation (`actions/attest`), and signs them with
cosign, keyless: Sigstore certifies this workflow's GitHub
OIDC identity, so no signing key exists to keep or to leak. Deploy smoke
verifies both for every deployed commit (`scripts/verify_images.sh`): the
certificate and the provenance must name `.github/workflows/ci.yml` of this
repository on `refs/heads/main`, that exact commit and a GitHub-hosted
runner; otherwise the promotion to production stops
(`docs/operations/deploys.md`, "Signed images").

### Dynamic scan

`.github/workflows/zap.yml` runs OWASP ZAP's baseline (passive) scans
against the running docker compose stack on every push to `main`, weekly,
and on pull requests that change the scan: the cabinet's public pages and
sign-in, a business's hosted chat page (`/c/{slug}`), the website widget,
and every read-only `/v1` operation with a seeded owner's bearer token.
The `/v1` scan must prove it was signed in: a hook records every answer
ZAP received (`scripts/zap_status_hook.py`) and `scripts/zap_auth_check.py`
fails the job unless the seeded business's routes answered 2xx at least
once and 401 for fewer than half of them. The job fails on every Medium or
High finding that `.zap/rules.tsv` has not reviewed, and on any finding of
a rule marked `FAIL` there (the security headers the cabinet and the API
promise). A reviewed exception names its rule (or one variant of it), the
addresses it covers and the reason, which the job summary repeats next to
the finding. It runs over plain http, so the https-only rules (HSTS, the
`Secure` cookie flag) are left to the header tests
(`tests/security/test_api_security_headers.py`, `web/e2e/security.spec.ts`).

`.github/workflows/zap-staging.yml` attacks as well: every Sunday an active
scan (injection, path traversal, server-side request forgery, ...) of
every operation of staging's public API, reads and writes, signed in with
an API key of a business that exists for the scan
(`STAGING_SCAN_API_KEY`), through the same `.zap/rules.tsv` gate. It never
runs against production, and it fails loudly when `STAGING_URL` or the key
is missing or never reached the API.

### Repository settings

These settings live in GitHub, not in a file:

- **Private vulnerability reporting** must stay on (*Settings > Code
  security > Private vulnerability reporting*): it is the first way to
  report above.
- **`main`** (a classic rule or a ruleset): changes arrive only through
  pull requests; the checks `CI passed (every gate)`, `Analyze (python)`,
  `Analyze (javascript-typescript)`, `Analyze (actions)`, `OpenAPI breaking
  changes (oasdiff)` and `Workflow audit (actionlint, zizmor)` must pass;
  force pushes and deleting the branch are blocked. `CI passed (every
  gate)` is one job that always runs and fails unless every other CI job
  succeeded: GitHub counts a required check whose job was skipped as
  passed. Approvals are not required while one maintainer reviews every
  change and Dependabot's grouped patch updates merge themselves
  (`automerge.yml`, after each workflow that owns a required check, once
  none is pending); raise `required_approving_review_count` to at least 1 and require
  Code Owners' review when a second maintainer joins (an owner action,
  `docs/security/roadmap.md`, SDLC-05): until then the author can merge a
  security-sensitive change alone.
- **`release`**, which production deploys, is protected like `main` by a
  ruleset whose only bypass is "Deploy keys". The one key with write
  access lives in the environment **`production-release`** (secret
  `RELEASE_DEPLOY_KEY`), which only workflows of `main` may use and whose
  required reviewers approve every promotion: no workflow token, branch
  workflow or automerged update can move `release` without a person.
  **`backup-drill`**, which holds the restore drill's private age key, is
  limited to `main` as well.

`.github/workflows/repo-settings.yml` reads all of this every morning with
`gh api`, together with Dependabot security updates, and fails when one is
off or weaker than `.github/repository-settings.json`
(`scripts/check_repository_settings.py`, `scripts/repository_environments.py`:
each environment exists, with exactly the expected reviewers and branch
rule). The workflow's own token cannot read these settings: it uses the
repository secret `REPO_SETTINGS_TOKEN`, a fine-grained token for this
repository only with *Administration: Read-only* and *Actions: Read-only*,
which can change nothing. A missing or expired token fails the check too
(renew it before it expires). The check cannot see a ruleset's bypass
actors or a reviewer team's members; the quarterly access review does
(`docs/security/access-review.md`). Change the expected settings only
together with the settings themselves, in a reviewed pull request.

### Dependency updates and the supply chain

- Dependabot (`.github/dependabot.yml`) proposes updates for Python, npm
  (the cabinet, the Zapier app, the Lighthouse tool), GitHub Actions,
  pip-audit's pins, Docker base images and the compose files every week,
  grouped; a new release waits 7 days (cooldown), so a compromised version
  is usually yanked before it arrives, while security updates come as soon
  as an advisory is published. This is how the DPA's promise of "regular
  updates of software dependencies" (section 9.1) is kept.
- Every image is pinned by tag and digest: Dockerfile bases and syntax
  image, workflow services, k6, the compose files.
- Nothing runs at install: npm install scripts are off (`ignore-scripts`
  in `web/`, the Zapier app and the Lighthouse tool) and uv builds no
  source distribution (`no-build`). CI's own tools come pinned by version
  and SHA-256 or from hashed lockfiles (pip-audit, Lighthouse CI,
  actionlint, zizmor).
- Secrets reach only the steps that use them, every checkout drops its
  token (`persist-credentials: false`) and each job asks for the smallest
  permissions; the `security` job may write pull requests only to post the
  dependency review's summary (a fork's token stays read-only).
- A new direct dependency is measured on its registry before it merges
  (SDLC-02, the table above): one installed from a git repository, an
  address, a local path, the workspace or another index fails as
  `not-from-registry` and is never looked up (the registry's facts say
  nothing about it), also when only a known name's origin changes or it
  comes through a PEP 508 `name @ url` or `[tool.uv.sources]`; an npm alias
  `npm:other@1` is measured as `other`; names in one npm scope are not
  compared with each other, since only the scope's owner publishes there.
  A change of the package index itself (`[[tool.uv.index]]`,
  `index-url`, `registry=` in `web/.npmrc`) is not measured and rests on
  the review of `.github/` and the dependency review.
- The cabinet's build is scanned for secrets before it is kept (WEB-05):
  key shapes in every file of `.next/static` and `.next/server`, and, when
  the build's environment holds them (CI's does not), the values of secret
  variables in what browsers receive (`.next/static` and the prerendered
  pages); a hit is fixed in the code and a real key is rotated. The cabinet's proxy drops `x-middleware-subrequest` (the
  middleware bypass of CVE-2025-29927) from every request it forwards
  (`web/src/server/middlewareSubrequest.ts`); the installed Next.js no
  longer reads it, a test holds Next.js at 16.0.7 or later and React at
  19.2.1 or later (`web/src/proxy.subrequest.test.ts`), and the sign-in
  redirect stays a convenience: the API authorizes every call.

### At run time

Production fails closed: with `APP_ENV=production` the API and every
worker refuse to start on an unsafe setting and name each one. Sign-in
codes are hashed under a server key and sensitive actions (deposit payment
pages included) need a fresh sign-in. A proof that raises a session to
two factors (a step-up, a new authenticator, a first passkey) reaches only
a new token, through a one-time rotation ticket for the client that made
it, and page code never holds a session token; people can sign out
everywhere, platform admins can end a member's sessions, and becoming an
owner ends one's sessions; new-country sign-ins and code spraying are
reported.
Webhook secrets rotate without refusing callbacks. The API checks webhook
signature headers before reading a body, limits anonymous callers,
bodies, JSON depth and request time, sends strict security headers and
writes refusals to a security log without personal data; the cabinet adds
its own CSRF rule, `Clear-Site-Data` at sign-out and a cookie banner.
Sentry events are scrubbed of personal data and log lines mask e-mail
addresses and phone numbers (the residuals are named on the page below).
The assistant reads customers' and owners' words only as fenced values,
its tools and contacts are capped, its replies are checked for team notes
and foreign links, it says it is an AI and names 112 in an emergency. A
caller ID never authenticates, in a call or in the missed-call text-back,
and a number is refused when any contact holding it is blocked; calls are
put through only to ordinary numbers of the business's country or the EU
(staff and manager numbers are checked when saved), recordings are off by
default; the platform can be paused and stops at its daily budget, its
background model work included; queued
jobs stay in their tenant; payments are reconciled daily; erasures survive
a restore and marketing waits for consent.

Added in the readiness round of 2026-11-03: platform admins sign in with a
passkey in production (`ADMIN_PASSKEY_REQUIRED`, also for a look into a
client's cabinet) and their sessions end after 15 idle minutes; sign-in
code alerts reach the admins at most once per key an hour in each process
(`app/facilitators/users/hourly_admin_alerts.py`); owners without
a second factor are asked at every one-factor sign-in; invitations to
accounts that never signed in lapse after 7 days; API keys and webhook
endpoints need a fresh sign-in, and a person who leaves or deletes the
account takes the keys they made with them. Guests' booking links can be
revoked; recordings are owner-only unless the owner lets staff play them.
Card numbers, security codes, IBANs and ID numbers are masked before
storage, the model, traces, logs and Sentry, and a call where a card was
read out keeps no audio; Flitt's callbacks count only once its status API
confirms them. The assistant may not claim a booking no tool made, stops
a conversation past its token, time or repeated-tool limits, stops a
business past ten times its daily spend limit in a month, and can be
switched off per action by the owner or for every business by a SUPER
admin; its customer memory keeps facts, not instructions. Text-backs go
only to mobiles of the business's country or the EU, trials without a card
have smaller caps and rent no number, fallback dials show the rented line,
and providers' raw error texts reach platform admins only. Tenant URLs are
fetched over https only through one provider HTTP client factory, the
widget loader is pinned with SRI, the consent ledger is append-only in the
database, and an erasure leaves salted digests that keep the customer out
of campaigns. Production refuses an external (dotted or IP) database
address that does not require TLS; a single-label private-network host
(Render's internal `dpg-…-a`) is exempt unless its query names another
server (`?host=`, `?hostaddr=`), so the Blueprints set no `PGSSLMODE`.
Integration circuits open only on provider outages, never on one
business's 4xx, and webhook signature bursts, storage errors, API latency,
backup failures and unused sign-in codes are platform alerts. Each measure with its code and
test: [docs/security/runtime-protections.md](docs/security/runtime-protections.md)
(the platform's edge) and
[docs/security/product-protections.md](docs/security/product-protections.md)
(the assistant, calls, bookings and money).

Added in the readiness round 2 of 2026-11-03: Flitt's and Stripe's
webhooks verify the signature, find the order and queue the notification
before they answer 200 `queued`; the job, sealed with the key ring and run
one at a time per order, reads Flitt's status back, applies each
(payment, status) once, and an approval that arrives after its payment's
refund or chargeback pays nothing. Five declined payments of one business
within two hours alert the platform (`tenant_payment_declines`) and ten
refuse its new checkout and card pages for a while (card testing). The
billing page's policy names no third-party host, and the scripts of the
payment pages are checked against a reviewed SHA-384 inventory in every
pull request and every week (against the files production serves once
the owner sets `PRODUCTION_CABINET_URL`; until then against a fresh build
of `main`). A change of the pages guests pay deposits on is also e-mailed
to every owner who signs in with an e-mail address (owners who sign in by
phone hear of it on their devices and the staff contacts only). A
cross-tenant matrix built from the API description calls every public API
operation, its query parameters included, with one business's key against
another's records. The audit log's 1,095-day purge runs daily on the platform role
through a database function that never removes a newer entry. A
customer's export lists the knowledge items that name them, and their
erasure flags those items for the owner instead of editing them. Booking
notes with health details are Restricted: they leave the platform in no
calendar event, staff message, public API answer or webhook, and only
the owner and staff see or change them in the cabinet. The website widget
writes nothing to the host site's storage until the visitor opens or uses
the chat. Sign-in stops sending codes to a new phone's number range, and
lowers its country's hourly cap, while too few of their codes of the last
six hours were used. A caller may ask for the call's transcript by
message; the phone assistant takes no keypad (DTMF) input, and the text
channels are the documented fallback. A return-visit campaign whose
customers opt out at 5 % or more is held for the platform team's review.
Per-business feature flags exist for staged rollouts, set only by SUPER
admins after a recent sign-in and audited; no code path reads one yet
(the registry's only flag, `release_canary`, guards nothing). Every
vertical's evaluation set has at least 100 scenarios with a hallucination
rate, and a pull request that touches what the model sees replays the
recorded answers of them all; the real models are measured by a nightly
run that stays skipped until the owner sets the provider keys. The
product's error budgets are computed from Prometheus in the Grafana
dashboard and `scripts/slo_report.py` (booking success is not measured
yet, and the admin System page still shows only the earlier budgets), and
the weekly `perf.yml` rehearses the pending migrations on a synthetic,
production-sized database (no rehearsal or rollback drill has run yet).
The
code and tests of each: [docs/security/threat-model.md](docs/security/threat-model.md)
(rows 2 to 5, 7, 12, 16, 22 and 34 to 40, with what stays open under
"Accepted risks").

Channel and calendar tokens are stored sealed with the newest key of
`ENCRYPTION_KEYS`; older keys only open what they sealed until a platform
admin's re-encryption run (`POST /v1/admin/security/encryption-keys/rotate`)
moves everything to the newest one. Off-site backups are encrypted with
age before they leave Render, into a bucket at another provider, in its own
account, with Object Lock (set up, and proven delete-denied once a year,
by the owner: `docs/operations/go-live.md`, section 6); their private keys
are held by the restore drill's own machine in the EU, at a provider the
DPA's list names, and in escrow, never by the service that writes the
backups. Production's backups are decrypted only on that machine;
GitHub-hosted runners restore synthetic data only (the workflow's
production job stays off). Custody, escrow and the rotation runbook:
[docs/operations/backup-restore.md](docs/operations/backup-restore.md).

### Governance documents

[docs/security/README.md](docs/security/README.md) lists the documents
that describe the platform's security, each with the test that keeps it
true: the generated inventory of every entry point and its access class,
the permission matrix, the secrets inventory with rotation, the data
classification with transfers and retention, the DPIA and the change risk
classes; and the management documents: the information security policy,
the risk register, the regulatory applicability register, the AI Act
record, the team's AI literacy training, the security and certification
roadmap (envelope encryption with a managed key, separate origins, an
admin origin, independent review) and the prepared security
questionnaire. A pull request carries a risk class; one labelled `risk:high` is
HIGH and needs the differential review of
[docs/security/change-risk.md](docs/security/change-risk.md).

## Triage of automated findings

- **Fix first.** Upgrade the dependency or change the code. A gate is never
  silenced with a blanket ignore.
- **A reviewed exception** names one finding, says why it does not apply,
  who reviewed it and when to look again:
  - `bandit-baseline.json`: regenerate only after reviewing every new entry
    (`uv run bandit -c pyproject.toml -r app scripts -f json -o bandit-baseline.json`,
    then keep only `metrics._totals`), and record it below;
  - `.gitleaksignore`: one fingerprint per finding, only for values that
    are not real secrets (fake test keys get an inline `# gitleaks:allow`);
  - `.trivyignore`: one vulnerability id per line with a comment and a
    review date;
  - `.zap/rules.tsv`: an `IGNORE` of one rule (or one variant of it) with
    its reason, or an `OUTOFSCOPE` address pattern with its reason in the
    comment above it, each with its review date; the gate refuses an
    exception without a reason.
- **A real secret that reached git** is revoked and rotated at once;
  removing it from history comes second.
- **Dependency advisories** of the nightly audit are fixed within a
  deadline counted from the day it first reported them: critical 2 days,
  high 7, moderate 30, low 90 (the next quarterly review). A Python
  advisory counts as high (pip-audit names no severity). The issue
  "Dependency advisories" lists each one with its deadline, and a critical
  or high one past its deadline turns `dependency-audit.yml` red. An
  advisory that cannot be fixed is accepted below, with its reason.

### Accepted findings (baseline of 2026-10-07, reviewed 2026-11-02)

| Tool | Where | Finding | Why it is accepted |
| --- | --- | --- | --- |
| bandit B311 | `app/registries/demo/load_dataset_registry.py` | seeded `random.Random` | Builds the repeatable bulk history of load-test businesses (`workshop seed-load`) from the run's seed; nothing in it is a secret, token or key. |
| gitleaks | `tests/billing/test_return_urls.py`, `tests/e2e/harness.py`, `tests/e2e/harness_settings.py` | generic API key | Made-up values of test settings in past commits. |
| gitleaks | `evals/cassettes/*.json` in commit `266501b` (1778 lines) | generic API key | SHA-256 digests of recorded model requests under a JSON field named `key`; the field is `request_digest` since, so re-recordings do not match. |
| gitleaks | `app/registries/niches/templates/b2b_supply_template.py` (commit `56f9e17`) and the `.gitleaksignore` comment that names it (commit `0d2c2e8`) | generic API key | The line `NICHE: NicheKey = …` assigns an enum member of the niche template; the name looks like a key to the generic rule but holds no secret. |
| gitleaks | `render.staging.yaml` in commit `c53c0e7` (lines 134, 267, 271) | generic API key | Names of environment variables (`RECORDINGS_S3_BUCKET`) of the staging API and worker, not values (reviewed 2026-11-02). |
| npm audit (not gated) | `.github/tools/lhci` (`@lhci/cli` 0.15.1, the latest release) | 13 high advisories (extract-zip, tmp, basic-ftp, zod, through lighthouse and puppeteer-core), no compatible fix | Lighthouse CI runs only on ephemeral CI runners against the locally built cabinet, from a lockfile with install scripts off; it never reaches users or production. Dependabot and GitHub's dependency alerts watch the tool; the nightly audit covers only what users and production run. Look again with every `@lhci/cli` release (reviewed 2026-11-02). |
