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

- the HTTP API (`/v1/...`) and its webhooks (Telegram, Meta, Flitt,
  ElevenLabs, Google Calendar callback);
- the website widget (`/widget.js`, `/v1/widget/...`);
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

Every pull request runs (`.github/workflows/`):

| Gate | Tool | Fails on |
| --- | --- | --- |
| Python dependencies | `pip-audit --strict` on the locked set (`uv export`) | any known vulnerability |
| Cabinet dependencies | `npm audit --omit=dev --audit-level=high` | high or critical in runtime packages |
| Secrets in the whole history | `gitleaks` | any secret not reviewed in `.gitleaksignore` |
| Python static analysis | `bandit` with `bandit-baseline.json` | any finding not in the dated baseline |
| Semantic analysis | CodeQL (Python, JavaScript/TypeScript, `security-extended`) | new high-severity alerts |
| Container images | Trivy on the backend and cabinet images | HIGH or CRITICAL with a fix available |
| Software bill of materials | syft (SPDX JSON per image, kept 30 days as a CI artifact) | — |
| API contract | `oasdiff breaking` against the merge base | breaking changes without the `api-breaking` label |
| Action pinning | `tests/platform/test_ci_workflows.py` | an action not pinned to a commit SHA |

### Signed images and build provenance

On every push to `main`, after every gate passed, CI publishes the backend
and cabinet images it built and scanned to ghcr.io under the commit SHA,
attaches SLSA build provenance (`actions/attest-build-provenance`) and
signs them with cosign, keyless: Sigstore certifies this workflow's GitHub
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
The job fails on every Medium or High finding that `.zap/rules.tsv` has not
reviewed, and on any finding of a rule marked `FAIL` there (the security
headers the cabinet and the API promise). A reviewed exception names its
rule (or one variant of it), the addresses it covers and the reason, which
the job summary repeats next to the finding. The scan never attacks
(no active scan). It runs over plain http, so the https-only rules (HSTS,
the `Secure` cookie flag) are left to the header tests
(`tests/security/test_api_security_headers.py`, `web/e2e/security.spec.ts`).

### Repository settings

Two settings this policy relies on live in GitHub, not in a file:

- **Private vulnerability reporting** must stay on (*Settings > Code
  security > Private vulnerability reporting*): it is the first way to
  report above.
- **Branch protection of `main`** (a classic rule or a ruleset): changes
  arrive only through pull requests, the CI, CodeQL and API contract
  checks must pass, force pushes and deleting the branch are blocked.
  Approvals are not required while one maintainer reviews every change
  and Dependabot's grouped patch updates merge themselves
  (`automerge.yml`); raise `required_approving_review_count` when a second
  maintainer joins.

`.github/workflows/repo-settings.yml` reads both every morning with
`gh api`, together with Dependabot security updates, and fails when one is
off or weaker than `.github/repository-settings.json`
(`scripts/check_repository_settings.py`). The workflow's own token cannot
read these settings: it uses the repository secret `REPO_SETTINGS_TOKEN`, a
fine-grained token for this repository only with *Administration:
Read-only*, which can change nothing. A missing or expired token fails the
check too (renew it before it expires), and `schedule-watch.yml` opens an
issue when the check has not succeeded for eight days. Change the expected
settings only together with the settings themselves, in a reviewed pull
request.

### Dependency updates

Dependabot (`.github/dependabot.yml`) proposes updates for Python, npm,
GitHub Actions and Docker base images every week, grouped, after a short
cooldown; security updates arrive as soon as an advisory is published. This
is how the DPA's promise of "regular updates of software dependencies"
(section 9.1) is kept; the daily repository settings check above keeps
Dependabot security updates switched on.

### At run time

- Sign-in codes cannot be guessed in parallel: each check takes one of the
  challenge's attempts atomically before the code is compared, checks are
  limited per client network and per challenge, and a right code opens one
  session (compare-and-swap).
- Codes are not sent to premium-rate, shared-cost or satellite numbers;
  codes to new phones are capped per country, verified users have a budget
  of their own, a cap that trips alerts the platform admins, and risky
  requests need a Cloudflare Turnstile check (README, "Защита входа").
- The API sends `nosniff`, `Referrer-Policy`, `X-Frame-Options`,
  `frame-ancestors 'none'`, `no-store` on `/v1` and HSTS in production,
  serves no `/docs` or `/openapi.json` in production and refuses request
  bodies over the route's limit (413). The cabinet sends a nonce-based CSP,
  HSTS, COOP and CORP, keeps the session in a `__Host-` cookie and applies
  the same body limits (web/README.md, "Security notes").
- Channel and calendar tokens are stored sealed with the newest key of
  `ENCRYPTION_KEYS`; older keys only open what they sealed until a platform
  admin's re-encryption run (`POST /v1/admin/security/encryption-keys/rotate`)
  moves everything to the newest one. Off-site backups are encrypted with
  age before they leave Render; their private keys are held by the restore
  drill (a GitHub environment secret) and in escrow, never by the service
  that writes the backups. Custody, escrow and the rotation runbook:
  [docs/operations/backup-restore.md](docs/operations/backup-restore.md).

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

### Accepted findings (baseline of 2026-10-07)

| Tool | Where | Finding | Why it is accepted |
| --- | --- | --- | --- |
| bandit B311 | `app/registries/demo/load_dataset_registry.py` | seeded `random.Random` | Builds the repeatable bulk history of load-test businesses (`workshop seed-load`) from the run's seed; nothing in it is a secret, token or key. |
| gitleaks | `tests/billing/test_return_urls.py`, `tests/e2e/harness.py`, `tests/e2e/harness_settings.py` | generic API key | Made-up values of test settings in past commits. |
| gitleaks | `evals/cassettes/*.json` in commit `266501b` (1778 lines) | generic API key | SHA-256 digests of recorded model requests under a JSON field named `key`; the field is `request_digest` since, so re-recordings do not match. |
| gitleaks | `app/registries/niches/templates/b2b_supply_template.py` (commit `56f9e17`) and the `.gitleaksignore` comment that names it (commit `0d2c2e8`) | generic API key | The line `NICHE: NicheKey = …` assigns an enum member of the niche template; the name looks like a key to the generic rule but holds no secret. |
