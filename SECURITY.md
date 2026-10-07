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
- Do **not** open a public issue, pull request or discussion about it.
- Include what you found, where (route, page, file), how to reproduce it,
  what an attacker gains, and any proof of concept. Use test accounts and
  your own data only.

The cabinet publishes this contact as `/.well-known/security.txt`
(`web/public/.well-known/security.txt`, RFC 9116); a test fails 30 days
before its `Expires`, so it is renewed in time. The trust boundaries, the
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

Dependabot (`.github/dependabot.yml`) proposes updates for Python, npm,
GitHub Actions and Docker base images every week, grouped, after a short
cooldown; security updates arrive as soon as an advisory is published. This
is how the DPA's promise of "regular updates of software dependencies"
(section 9.1) is kept.

At run time:

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
    review date.
- **A real secret that reached git** is revoked and rotated at once;
  removing it from history comes second.

### Accepted findings (baseline of 2026-10-07)

| Tool | Where | Finding | Why it is accepted |
| --- | --- | --- | --- |
| bandit B311 | `app/registries/demo/load_dataset_registry.py` | seeded `random.Random` | Builds the repeatable bulk history of load-test businesses (`workshop seed-load`) from the run's seed; nothing in it is a secret, token or key. |
| gitleaks | `tests/billing/test_return_urls.py`, `tests/e2e/harness.py`, `tests/e2e/harness_settings.py` | generic API key | Made-up values of test settings in past commits. |
| gitleaks | `evals/cassettes/*.json` in commit `266501b` (1778 lines) | generic API key | SHA-256 digests of recorded model requests under a JSON field named `key`; the field is `request_digest` since, so re-recordings do not match. |
| gitleaks | `app/registries/niches/templates/b2b_supply_template.py` (commit `56f9e17`) and the `.gitleaksignore` comment that names it (commit `0d2c2e8`) | generic API key | The line `NICHE: NicheKey = …` assigns an enum member of the niche template; the name looks like a key to the generic rule but holds no secret. |
