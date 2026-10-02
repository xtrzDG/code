## What and why

<!-- What changes for owners, customers or operators, and why. Link the plan item or issue. -->

## How it was checked

<!-- Tests added or changed; for the cabinet: pages checked in a browser (dark and light, 1440 and 390 px). -->

## Checklist

- [ ] `just check` passes (ruff, mypy, pyright, pytest with coverage ≥ 95 %; cabinet lint, typecheck, tests with coverage, build).
- [ ] New behaviour has tests; nothing reaches the network in tests (fakes implement contracts).
- [ ] Domain values use typed primitives; the role chain and `.importlinter` layers hold.
- [ ] **Database:** new SQL migration in `migrations/` (never edit an applied one), safe for a rolling deploy (old code keeps working on the new schema).
- [ ] **Stored documents:** a changed document schema still reads old rows (new fields optional or defaulted, a schema version bump and upcaster when a field changes meaning).
- [ ] **API:** `cd web && npm run gen:api` run and `openapi.json` + `src/api/schema.d.ts` committed; changes within `/v1` are additive (`docs/api-versioning.md`); an entry with the new `Spec:` fingerprint on top of `docs/API_CHANGELOG.md`.
- [ ] **Personal data:** views, exports, deletions and admin access write an audit entry; nothing personal goes to logs or traces.
- [ ] **Configuration:** new environment variables are in the settings section, `.env.example`, the README table and `docs/LAUNCH.md`.
- [ ] **Cabinet texts:** every new text in en, ru and ka (real translations), UI kit and design tokens used, works at 390 px and with a keyboard.
- [ ] **Security:** no new gate exception (bandit baseline, `.gitleaksignore`, `.trivyignore`, vulture whitelist) without a reason recorded in `SECURITY.md` or the file itself.
