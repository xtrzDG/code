# Change risk and differential review

Every pull request names its risk class in the template
(`.github/pull_request_template.md`). A **HIGH** change gets a
differential review: a second person reads what the change does to the
trust boundaries, not only whether the code is tidy.
`tests/legal/test_change_risk.py` keeps this list in step with
`.github/CODEOWNERS` (every path the owners must approve is HIGH here) and
with the `risk:high` label, and checks that every path below exists.

## Classes

**HIGH** when the pull request carries the `risk:high` label, which
`.github/workflows/risk-labels.yml` sets by itself from the paths of
`.github/labeler.yml` (sign-in, keys, payments, webhooks, tenant
isolation, the assistant's tools, CI and images); when it touches any of
these; or when it does any of the things after the list:

- `app/gateways/http/user_authentication.py`, `app/gateways/http/api_key_authentication.py`
  and `app/use_cases/authorize_business_access_use_case.py`,
  `app/use_cases/authorize_support_access_use_case.py`,
  `app/utilities/brands/brand_access.py`: who is let in;
- `app/adapters/security/`, `app/utilities/security/`: keys, ciphers,
  signed links, sessions, admin permissions;
- `app/repositories/business_scoped_repository.py`, `app/utilities/storage/`
  and migrations of row-level security or database roles (`migrations/`):
  one business's data apart from another's;
- `app/utilities/channels/webhook_signatures.py`,
  `app/utilities/channels/voice_webhook_auth.py`, `app/clients/flitt/`,
  `app/clients/stripe/`: provider callbacks and money;
- `app/use_cases/conversations/tools/`: what the model can do;
- `app/registries/legal/` and `docs/legal/`: the sub-processors, the
  security measures and the texts the businesses accepted;
- `app/repositories/audit/` and `app/use_cases/compliance/`: the audit log,
  exports and erasure;
- `tests/platform/route_access_tables.py`, `tests/platform/authorization_tables.py`,
  `tests/platform/brand_matrix_checks.py`: the reviewed exceptions of the
  authorization tests, and `scripts/entry_points/`: how the entry-point
  inventory classifies what those tables do not name;
- `web/src/server/`: the cabinet's server (session cookie, proxy, CSP);
- `.github/`, `Dockerfile`, `web/Dockerfile`, `docker/`, `render.yaml`,
  `.importlinter`, `bandit-baseline.json`, `.gitleaksignore`,
  `.trivyignore`, `vulture_whitelist.py`, `SECURITY.md`: the supply chain,
  the deployment and the gates themselves;
- `web/openapi.json`, `docs/API_CHANGELOG.md`, `docs/api-versioning.md`:
  the contract others build on.

and also when it:

- adds a `public`, `signed_webhook`, `customer` or `api_key` entry point,
  or moves an operation to a weaker class
  (`docs/security/entry-points.json` shows it in the diff);
- changes what a role may do (`docs/security/permission-matrix.md`);
- adds a secret, a sub-processor, a new kind of personal data or a new
  transfer (`docs/security/secrets-inventory.md`,
  `docs/security/data-classification.md`, `docs/operations/vendor-register.md`);
- adds or relaxes an exception of a gate (bandit, gitleaks, trivy, vulture,
  an architecture test).

**MEDIUM**: new behaviour inside the existing trust boundaries: a staff or
owner operation, a migration that adds tables or columns, a new stored
document field without new personal data, a new dependency, an alert rule.

**LOW**: documentation, texts of the cabinet, styles, tests only, refactors
that change no behaviour.

When unsure, pick the higher class.

## Differential review of a HIGH change

The reviewer is not the author and is a code owner of the paths touched;
when the author is the only code owner (one owner today, `.github/CODEOWNERS`),
the deputy of `docs/operations/contacts.md` reviews, and the owner approves
only after the answers are in. A pull request an AI agent wrote counts as
written by the person who ran the agent. The reviewer answers these in the
pull request, each with "yes", "no" or "n/a" and a line of why:

1. **Entry points**: does the diff of `docs/security/entry-points.json`
   add or weaken one? Is each new open entry point in
   `tests/platform/route_access_tables.py` with a reason a reader can check?
2. **Authorization**: does the diff of `docs/security/permission-matrix.md`
   match what the change means to allow? Is there a test where the wrong
   role, another business and no token are refused?
3. **Data**: does personal data reach a new place (a table, a log, a
   provider, an export)? Is it in the erasure, the retention and the
   classification?
4. **Secrets**: is a new secret in the inventory, read only on the server,
   never logged, refused when missing in production?
5. **Failure**: what does the change do when its provider is slow, down or
   lying (a forged webhook, a replay)? Is that tested?
6. **Rollback**: can the previous release run against the state this one
   leaves (`docs/operations/deploys.md`)? What is the rollback?

The reviewer reads the diff against the merge base, not only the last
commit, and runs the tests named in the answers. A HIGH change that may
interrupt answering ships in the maintenance window
(`docs/operations/maintenance.md`), never on Friday or in a freeze.
