## What and why

<!-- What changes for owners, customers or operators, and why. Link the plan item or issue. -->

## Risk

<!-- One of HIGH, MEDIUM, LOW (docs/security/change-risk.md) and one line of why. When unsure, the higher one. -->

Risk: 

## How it was checked

<!-- Tests added or changed; for the cabinet: pages checked in a browser (dark and light, 1440 and 390 px). -->

## Differential review (HIGH only)

<!-- The reviewer, not the author, answers each with yes / no / n/a and a line of why (docs/security/change-risk.md). Delete this section for MEDIUM and LOW. -->

- [ ] **Entry points:** the diff of `docs/security/entry-points.json` adds or weakens nothing unexplained; each new open entry point has its reason in `tests/platform/route_access_tables.py`.
- [ ] **Authorization:** the diff of `docs/security/permission-matrix.md` matches what the change means to allow; tests refuse the wrong role, another business and no token.
- [ ] **Data:** new personal data is covered by erasure, retention and `docs/security/data-classification.md`; a new provider is in `docs/operations/vendor-register.md` and announced (DPA 8.3).
- [ ] **Secrets:** a new secret is in `docs/security/secrets-inventory.md`, server-side only, never logged, refused when missing in production.
- [ ] **Failure:** behaviour when the provider is slow, down or forged is tested.
- [ ] **Rollback:** the previous release runs on the state this one leaves; the rollback is written here.

## Checklist

- [ ] `just check` passes (ruff, mypy, pyright, pytest with coverage ≥ 95 %; cabinet lint, typecheck, tests with coverage, build).
- [ ] New behaviour has tests; nothing reaches the network in tests (fakes implement contracts).
- [ ] Domain values use typed primitives; the role chain and `.importlinter` layers hold.
- [ ] **Entry points:** `uv run python -m scripts.entry_point_inventory` run when routes, jobs or commands changed, and both generated files committed.
- [ ] **Database:** new SQL migration in `migrations/` (never edit an applied one), safe for a rolling deploy (old code keeps working on the new schema).
- [ ] **Stored documents:** a changed document schema still reads old rows (new fields optional or defaulted, a schema version bump and upcaster when a field changes meaning).
- [ ] **API:** `cd web && npm run gen:api` run and `openapi.json` + `src/api/schema.d.ts` committed; changes within `/v1` are additive (`docs/api-versioning.md`); an entry with the new `Spec:` fingerprint on top of `docs/API_CHANGELOG.md`.
- [ ] **Personal data:** views, exports, deletions and admin access write an audit entry; nothing personal goes to logs or traces.
- [ ] **Configuration:** new environment variables are in the settings section, `.env.example`, the table of `docs/dev/environment.md` and `docs/LAUNCH.md`; new secrets also in `docs/security/secrets-inventory.md`.
- [ ] **Cabinet texts:** every new text in English and Italian (natural translations), UI kit and design tokens used, works at 390 px and with a keyboard.
- [ ] **Security:** no new gate exception (bandit baseline, `.gitleaksignore`, `.trivyignore`, vulture whitelist) without a reason recorded in `SECURITY.md` or the file itself.
