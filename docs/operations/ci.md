# CI: layout, time budget and the durations files

`.github/workflows/ci.yml` runs on every pull request and every push to
`main`. Its budget: **under eight minutes from the push to the last job**.
The last job (`durations`, `scripts/ci_job_durations.py`) writes every job's
duration to the run summary, slowest first, and warns about each job over
eight minutes. Run 37537772194 (commit dd254a9) took 19 minutes with two
backend parts, one cabinet job and four end-to-end shards; this page
describes the layout that replaced it and how to keep it balanced.

## The jobs

Everything starts at once except `coverage` (after every backend part),
`e2e` and `visual` (after `web-build`) and `durations` (after everything).

| Job | What it does | Waits for | Expected |
| --- | --- | --- | ---: |
| `backend-checks` | ruff, mypy, pyright, legal texts, the duplication ratchet (jscpd, `docs/dev/code-health.md`) | — | ~2:25 |
| `backend-tests` (postgres 1/2, 2/2; rest 1/4 … 4/4) | pytest with coverage on four xdist workers, one part of a group each | — | ~4:15 (tests ~3:15) |
| `coverage` | combines every part's coverage (floor 95 %), merges the parts' durations into the `backend-test-durations` artifact | `backend-tests` | ~0:30 |
| `web-build` | `npm ci`, `.next/cache` restored, `next build`, the build kept as the `cabinet-build` artifact | — | ~1:45 (build ~1:00) |
| `web-checks` | check:intl, lint, knip, typecheck, vitest with coverage, generated client; on `main` the Sentry source maps | — | ~2:45 |
| `security` | pip-audit, npm audit, gitleaks, bandit | — | ~0:40 |
| `images` | both Docker images: build, smoke test, Trivy, SBOM | — | ~3:50 |
| `e2e` (1/10 … 10/10) | starts the downloaded build and its own API, runs its spec files | `web-build` | ~4:40 (tests ~3:30) |
| `visual` | the visual tests and the review gate (`web/README.md`): starts the downloaded build and an API whose clock starts at a fixed moment, the browser in Playwright's image (pulled at the job's start, in the background), compares 222 screenshots; keeps the differences on failure | `web-build` | ~5:00 (tests ~3:20) |
| `publish-images` (`main` only) | pushes the two images `images` built and scanned to ghcr.io under the commit SHA, with SLSA build provenance and a keyless cosign signature, then verifies both (`scripts/verify_images.sh`) | every gate above | not measured yet |
| `durations` | the run summary of every job's duration | all | ~0:20 |

The critical path is `web-build` → `visual` → `durations`: about 1:45 +
5:00 + 0:20, about seven minutes (the slowest `e2e` shard ends some
twenty seconds before `visual`). The backend path
(`backend-tests` → `coverage`) ends about 4:45 after the push. At most 20
jobs run at the same time (ten shards, `visual`, six backend parts and
three others: `backend-checks`, `web-checks` and `images` are still running
when `web-build` ends), the 20 that GitHub runs at once for a free
account: a new job that overlaps them would queue, so it goes after one of
them or replaces one.
Wave 22's closing of a business brought the suite to about 2037 seconds,
more than nine shards hold within their budget (9 × 225), so a tenth
shard was added; branch protection requires only "CI passed (every
gate)", which waits for every shard whatever their count.

Expected times are local measurements scaled to GitHub's runners (public
repository: four vCPUs, the same core count as the machine they were
measured on). Run 37537772194 gave the scale: its four e2e shards' test
steps took 1.03–1.16 times the seconds the same specs took locally, plus
about 15 seconds to start the API and the cabinet, and each shard about
70 seconds more for its setup (checkout, uv and npm installs, Chromium,
the build's download). `web/e2e/durations.json` comes from one later
local run of the whole suite on a machine busy with other work, whose
specs took 1.22 times as long as in that calibrating local run: every
duration was scaled by 0.86 (1.05 / 1.22) to CI's runners, and a shard of
the plan holds about 204 of those seconds. `tests/durations.json` comes
from one local run of the whole backend suite on four xdist workers, scaled
per group so that each group's sum matches the worker-seconds of run
37537772194: its `rest` part spent 679 seconds in pytest and its `postgres`
part 283, about 30 of each collecting, on four workers (factors 0.53 and
0.76). Each part of the plan holds about 650 (rest) or 506 (postgres) of
those seconds, about 2:45 and 2:10 on four workers plus the collection;
the slowest Postgres file (the chaos game days, about 157 seconds) sets
the floor of its part.

## Signed images, the dynamic scan and the repository settings

- `publish-images` runs only for a push to `main`, after every gate. The
  images are the ones `images` built and scanned (a saved artifact, not a
  rebuild). Signing is keyless: Sigstore issues a short-lived certificate
  for this workflow's OIDC identity (`ci.yml` on `refs/heads/main`), so
  there is no signing key to keep or leak. Deploy smoke runs the same
  `scripts/verify_images.sh` for every deployed commit
  (`docs/operations/deploys.md`, "Signed images").
- `zap.yml` (OWASP ZAP baseline, at most 45 minutes) starts the docker
  compose stack with a scripted model, seeds one business and scans the
  cabinet, the hosted chat page, the widget and every read-only `/v1`
  operation with the owner's token. It runs on every push to `main`, every
  Tuesday for ZAP's newer rules, and on pull requests that change the scan.
  `scripts/zap_gate.py` fails it on any Medium or High finding
  `.zap/rules.tsv` has not reviewed (SECURITY.md, "Dynamic scan"); the job
  summary lists every finding with the reason of each reviewed exception.
  `scripts/zap_auth_check.py` fails it when the `/v1` scan was not signed
  in (the seeded business's routes answered 401 instead of 2xx).
- `repo-settings.yml` checks every morning that branch protection, private
  vulnerability reporting and Dependabot security updates are as
  `.github/repository-settings.json` expects (SECURITY.md, "Repository
  settings"). The required checks there are `CI passed (every gate)`
  (the last job of `ci.yml`, which always runs and fails unless every other
  CI job succeeded: a required job that was skipped because a job it needs
  failed would count as passed) and the jobs of `codeql.yml` and
  `api-contract.yml`: renaming a job means changing that file and the
  branch protection together (`tests/platform/test_supply_chain_workflows.py`
  and `tests/platform/test_release_paths.py` fail until both agree).
- `automerge.yml` merges a green grouped Dependabot update after each of
  the workflows that own a required check (CI, CodeQL, API contract) and
  only once none of those checks is pending. Its merge, made with the
  workflow's token, pushes no event, so it then starts every workflow a
  push to `main` starts: CI (whose run on `main` publishes the signed
  images deploy smoke verifies), CodeQL, Lighthouse and the ZAP baseline.

## Backend tests in parts

`tests/conftest.py` marks the tests that reach Postgres (`postgres`); CI
runs that group (`-m "postgres and not perf"`) and the rest
(`-m "not postgres and not perf"`) in parts. With `TEST_PART=k/n` a run
keeps, after `-m` chose the group, only the test files that
`tests/part_plan.py` gives part k of n: every file of the group weighs the
seconds its tests took in `tests/durations.json` (a file not measured yet
weighs the mean of its group), and files go, longest first, to the part
with the least work. Every part and every xdist worker computes the same
plan from the same collection. The parts write `.coverage.<group>-<k>`;
the `coverage` job combines them and checks the 95 % floor on the sum.

`tests/platform/test_ci_test_parts.py` fails when a part of the committed
plan holds more measured seconds than its budget (add a part to the matrix
or split the slow files) and warns about files without a duration.

## Cabinet: build next to the checks

`web-build` only builds: it restores `web/.next/cache` (Turbopack's build
cache; key: the lockfile and a hash of `web/src`, `web/public` and
`next.config.ts`, falling back to the newest cache of the same lockfile),
runs `next build` and keeps `.next` without its cache as `cabinet-build`.
Locally the first build of this worktree took 1:44, a later one of the
same sources 13 seconds from that cache (about 260 MB); after a change only
what it touched compiles again.
The e2e shards need only this job. `web-checks` runs everything else at
the same time and holds the Sentry token on `main`, so the shards' build
never sees it. npm's download cache comes from `setup-node`, uv's from
`setup-uv` (`enable-cache`).

## Visual tests

`visual` runs `npm run e2e:visual` once, not in shards: its 222 pictures
take about three minutes on three workers (`web/e2e/visual/project.ts`), and
its first project (the demo owner's sign-in, the platform admin's pages)
must run before the rest. It installs neither a browser nor the PDF
engine's libraries: the browser is the one of Playwright's image, pinned by
digest in `web/scripts/visual-browser.mjs`, which the job pulls (about 1 GB)
in the background while uv and npm install, and the pages are only looked
at. On failure it keeps the expected, actual and diff PNG of every
differing screen with the HTML report (`visual-report`).

## End-to-end shards

`web/e2e/support/shards.ts` gives each shard its spec files: every spec
weighs the seconds it took in `web/e2e/durations.json` (a spec not measured
yet weighs the mean, and the shard prints a warning), and specs go, longest
first, to the shard with the least work. Every shard starts its own API
with in-memory storage, and every spec builds what it needs there (an
owner signs up; a platform admin is added to the team by the run's first
admin, `support/admin.ts`), so any spec may run on any shard. A worker
reuses an admin's sign-in for a few minutes: a second sign-in of the same
address would wait out the 30-second code cooldown, and a spec's duration
would depend on its neighbours.

The PDF engine's libraries (WeasyPrint's Pango) and the browser's system
libraries and fonts (`playwright install --with-deps`, about 22 MB from
Ubuntu's mirror) come from the Actions cache, keyed by the runner image and
`web/package-lock.json`: some runners reach the mirror at 30 kB/s or not at
all. On 23 October 2026 the browser's packages took 9 to 13 minutes of
three shards' 15; on 26 October `apt-get update` itself stalled until a
shard's timeout. On a hit, dpkg installs the cached packages without apt
(no `apt-get update`): they are what an earlier run of this workflow
fetched and apt checked against the signed index, and only this
repository's own runs write the cache. On a miss, apt fetches them with
timeouts and retries and the cache keeps what it downloaded.

`web/e2e/support/shards.test.ts` (part of `npm test`) fails while a spec
has no duration, an entry names a spec that is gone, or a shard of the plan
for the matrix in `ci.yml` holds more than its budget: 225 seconds of specs,
which with the 15 seconds that start the API and the cabinet keep a
shard's test step within four minutes. A long spec file is split so that
no file holds more than about half a shard: the route tour runs as
`tour-routes*.spec.ts` (all in the Tbilisi project, `e2e/support/tour.ts`),
the audit of every section as `a11y-sections-en.spec.ts` and
`a11y-sections-he.spec.ts` (`e2e/support/axe.ts`), the long texts as
`pseudo-locale-ltr.spec.ts` and `pseudo-locale-rtl.spec.ts`
(`e2e/support/long-texts.ts`).

## Refreshing the durations files

Refresh after adding, splitting or noticeably slowing down tests, or when
the run summary shows one part or shard well above the others. Both files
hold seconds on CI's runners, so CI's own reports are the best source; a
run on an idle four-core machine measures about the same (CI took 1.03–1.16
times as long), a run on a busy or faster machine needs scaling first.

The end-to-end specs (`web/e2e/durations.json`):

```bash
cd web
npm run e2e:durations                         # the whole suite, about 25 minutes
npm run e2e:durations -- inbox.spec.ts        # only these files; the other entries stay
# Or from a CI run, measured on CI's machines:
gh run download <run-id> --pattern 'e2e-report-*' --dir /tmp/e2e-reports
npm run e2e:durations -- $(for f in /tmp/e2e-reports/*/.artifacts/report.json; do printf -- '--from %s ' "$f"; done)
```

`scripts/e2e-durations.mjs` runs Playwright with its JSON reporter (on CI
every shard writes `e2e/.artifacts/report.json` into its `e2e-report-<k>`
artifact), adds up each spec file's tests (every project and attempt) and
rewrites the file: measured specs replace their entries, specs that are
gone are dropped. A run with a failed test writes nothing.

The backend test files (`tests/durations.json`):

```bash
TEST_DURATIONS_REPORT=/tmp/durations-report.json uv run pytest -n auto \
    --cov=app --cov-branch --cov-report= --cov-fail-under=0
uv run python -m scripts.backend_test_durations /tmp/durations-report.json
# Or from a CI run: its `backend-test-durations` artifact is the merged file.
gh run download <run-id> --name backend-test-durations --dir tests
```

With `TEST_DURATIONS_REPORT` the run's controller (`tests/duration_recorder.py`)
writes each test file's seconds (setup, call and teardown) by group;
`scripts/backend_test_durations.py` merges one or more such reports into
the committed file the same way. Every CI part writes its report into its
`coverage-<group>-<k>` artifact, and the `coverage` job merges them.

Commit the refreshed file with the change that made it necessary; CI's
own numbers are the better source once a run has them.
