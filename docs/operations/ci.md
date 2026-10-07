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
`e2e` (after `web-build`) and `durations` (after everything).

| Job | What it does | Waits for | Expected |
| --- | --- | --- | ---: |
| `backend-checks` | ruff, mypy, pyright, legal texts | — | ~2:15 |
| `backend-tests` (postgres 1/2, 2/2; rest 1/4 … 4/4) | pytest with coverage on four xdist workers, one part of a group each | — | ~4:15 (tests ~3:15) |
| `coverage` | combines every part's coverage (floor 95 %), merges the parts' durations into the `backend-test-durations` artifact | `backend-tests` | ~0:30 |
| `web-build` | `npm ci`, `.next/cache` restored, `next build`, the build kept as the `cabinet-build` artifact | — | ~1:45 (build ~1:00) |
| `web-checks` | check:intl, lint, knip, typecheck, vitest with coverage, generated client; on `main` the Sentry source maps | — | ~2:45 |
| `security` | pip-audit, npm audit, gitleaks, bandit | — | ~0:40 |
| `images` | both Docker images: build, smoke test, Trivy, SBOM | — | ~3:50 |
| `e2e` (1/8 … 8/8) | starts the downloaded build and its own API, runs its spec files | `web-build` | ~4:40 (tests ~3:30) |
| `durations` | the run summary of every job's duration | all | ~0:20 |

The critical path is `web-build` → the slowest `e2e` shard → `durations`:
about 1:45 + 4:40 + 0:20, under seven minutes. The backend path
(`backend-tests` → `coverage`) ends about 4:45 after the push. At most 17
jobs run at the same time (eight shards, six backend parts and three
others), within the 20 that GitHub runs at once for a free account.

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
the plan holds about 194 of those seconds. `tests/durations.json` comes
from one local run of the whole backend suite on four xdist workers, scaled
per group so that each group's sum matches the worker-seconds of run
37537772194: its `rest` part spent 679 seconds in pytest and its `postgres`
part 283, about 30 of each collecting, on four workers (factors 0.53 and
0.76). Each part of the plan holds about 650 (rest) or 506 (postgres) of
those seconds, about 2:45 and 2:10 on four workers plus the collection;
the slowest Postgres file (the chaos game days, about 157 seconds) sets
the floor of its part.

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
