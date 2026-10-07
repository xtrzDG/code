"""CI stays fast and its dependency updates stay safe.

The backend tests run in parts balanced by measured duration whose coverage
is combined, the cabinet's checks run next to its build, the end-to-end
suite in shards that start that build, a last job reports every duration
(docs/operations/ci.md); Dependabot's toolchain majors wait for a quarterly
issue and only grouped patch or minor updates merge themselves.
"""

import re
from pathlib import Path
from typing import Any, cast

import yaml

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
WORKFLOWS: Path = PROJECT_ROOT / ".github" / "workflows"
TOOLCHAIN_MAJORS: set[str] = {"typescript", "eslint", "@types/node"}


def load(path: Path) -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def triggers(workflow: dict[Any, Any]) -> dict[str, Any]:
    # YAML 1.1 reads the key `on` as True.
    return cast(dict[str, Any], workflow.get("on", workflow.get(True)))


def scalar(value: object) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def steps_text(job: dict[str, Any]) -> str:
    """Each step's commands and `with:` inputs, as written."""
    lines: list[str] = []
    for step in cast(list[dict[str, Any]], job["steps"]):
        lines.append(str(step.get("run", "")))
        inputs = cast(dict[str, object], step.get("with", {}))
        lines.extend(f"{key}: {scalar(value)}" for key, value in inputs.items())
    return "\n".join(lines)


CI: dict[Any, Any] = load(WORKFLOWS / "ci.yml")
JOBS: dict[str, Any] = CI["jobs"]


def test_the_backend_tests_run_in_parts_of_each_group() -> None:
    tests = JOBS["backend-tests"]
    parts: list[dict[str, Any]] = tests["strategy"]["matrix"]["include"]
    groups: dict[str, list[dict[str, Any]]] = {
        group: [part for part in parts if part["group"] == group]
        for group in ("postgres", "rest")
    }

    assert {part["group"] for part in parts} == {"postgres", "rest"}
    for group_parts in groups.values():
        total: int = group_parts[0]["parts"]
        assert [part["part"] for part in group_parts] == list(range(1, total + 1))
        assert {part["parts"] for part in group_parts} == {total}
    assert len(groups["rest"]) > 1
    assert tests["timeout-minutes"] <= 15
    assert "postgres and not perf" in tests["env"]["MARKERS"]
    assert "not postgres and not perf" in tests["env"]["MARKERS"]
    assert tests["env"]["TEST_PART"] == "${{ matrix.part }}/${{ matrix.parts }}"
    assert (
        tests["env"]["COVERAGE_FILE"]
        == ".coverage.${{ matrix.group }}-${{ matrix.part }}"
    )
    run = steps_text(tests)
    assert '-m "$MARKERS"' in run
    assert "--cov-fail-under=0" in run
    assert "include-hidden-files: true" in run
    assert "name: coverage-${{ matrix.group }}-${{ matrix.part }}" in run
    assert "${{ env.TEST_DURATIONS_REPORT }}" in run
    assert "enable-cache: true" in run


def test_every_parts_coverage_is_combined_and_holds_the_floor() -> None:
    coverage = JOBS["coverage"]
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert coverage["needs"] == "backend-tests"
    run = steps_text(coverage)
    assert "pattern: coverage-*" in run
    assert "coverage combine coverage-parts" in run
    assert "coverage report" in run
    assert "scripts.backend_test_durations coverage-parts/durations-*.json" in run
    assert "relative_files = true" in pyproject
    assert re.search(r"^fail_under = 95$", pyproject, re.MULTILINE)


def test_the_cabinet_checks_run_next_to_the_build_the_shards_start() -> None:
    build, checks, e2e = JOBS["web-build"], JOBS["web-checks"], JOBS["e2e"]
    build_run, checks_run = steps_text(build), steps_text(checks)

    assert "needs" not in build and "needs" not in checks
    assert "npm run build" in build_run
    assert "name: cabinet-build" in build_run
    assert "path: web/.next/cache" in build_run
    assert "hashFiles('web/package-lock.json')" in build_run
    assert "hashFiles('web/src/**'" in build_run
    for check in (
        "npm run check:intl",
        "npm run lint",
        "npm run knip",
        "npm run typecheck",
        "npm run test:coverage",
        "npm run gen:api:types",
    ):
        assert check in checks_run, check
        assert check not in build_run, check
    # The Sentry token never reaches the build the shards download.
    assert "SENTRY_AUTH_TOKEN" not in yaml.safe_dump(build)
    assert "cache: npm" in build_run and "cache: npm" in checks_run

    assert e2e["needs"] == "web-build"
    run = steps_text(e2e)
    assert "name: cabinet-build" in run
    assert "path: web/.next" in run
    assert "web/e2e/flaky.json" in run
    assert "web/e2e/.artifacts/report.json" in run


def test_the_end_to_end_shards_follow_the_shard_plan() -> None:
    e2e = JOBS["e2e"]
    shards: list[int] = e2e["strategy"]["matrix"]["shard"]
    total: int = len(shards)

    assert shards == list(range(1, total + 1))
    assert total >= 6
    assert e2e["name"] == f"End-to-end (${{{{ matrix.shard }}}}/{total})"
    tests = next(step for step in e2e["steps"] if step.get("run") == "npm run e2e")
    assert tests["env"] == {
        "E2E_SKIP_BUILD": "1",
        "E2E_SHARD": f"${{{{ matrix.shard }}}}/{total}",
    }
    # web/e2e/support/shards.test.ts reads the same count to check the budget.
    assert (PROJECT_ROOT / "web" / "e2e" / "durations.json").exists()


def test_the_last_job_reports_every_jobs_duration() -> None:
    durations = JOBS["durations"]

    assert set(durations["needs"]) == set(JOBS) - {"durations"}
    assert durations["if"] == "${{ !cancelled() }}"
    assert durations["permissions"] == {"actions": "read", "contents": "read"}
    assert "scripts.ci_job_durations" in steps_text(durations)


def test_dependabot_leaves_toolchain_majors_to_the_quarterly_issue() -> None:
    dependabot = load(PROJECT_ROOT / ".github" / "dependabot.yml")
    npm = next(
        update
        for update in dependabot["updates"]
        if update["package-ecosystem"] == "npm"
    )
    ignored = {rule["dependency-name"]: rule["update-types"] for rule in npm["ignore"]}
    quarterly = load(WORKFLOWS / "major-updates.yml")
    issue = steps_text(quarterly["jobs"]["issue"])

    assert ignored == dict.fromkeys(TOOLCHAIN_MAJORS, ["version-update:semver-major"])
    assert triggers(quarterly)["schedule"] == [{"cron": "23 7 1 1,4,7,10 *"}]
    assert quarterly["jobs"]["issue"]["permissions"] == {"issues": "write"}
    for name in TOOLCHAIN_MAJORS:
        assert name in issue


def test_only_a_green_dependabot_run_can_merge_and_only_its_head() -> None:
    automerge = load(WORKFLOWS / "automerge.yml")
    merge = automerge["jobs"]["merge"]
    run = steps_text(merge)

    assert triggers(automerge) == {
        "workflow_run": {"workflows": ["CI"], "types": ["completed"]}
    }
    assert CI["name"] == "CI"
    for condition in (
        "github.event.workflow_run.conclusion == 'success'",
        "github.event.workflow_run.actor.login == 'dependabot[bot]'",
        "head_repository.full_name == github.repository",
    ):
        assert condition in merge["if"]
    assert merge["permissions"] == {
        "actions": "write",
        "contents": "write",
        "pull-requests": "write",
    }
    assert "scripts.dependabot_automerge" in run
    assert '--match-head-commit "$HEAD_SHA"' in run
    # A conflicting group waits for Dependabot's rebase instead of failing.
    assert run.index('"$mergeable" = "CONFLICTING"') < run.index("gh pr merge")
    # A merge pushed with the job's token starts no CI: the job dispatches it.
    assert run.index("gh pr merge") < run.index('gh workflow run ci.yml --ref "$base"')
    assert "workflow_dispatch" in triggers(CI)
    # The pull request's code is never checked out.
    checkout = next(step for step in merge["steps"] if "uses" in step)
    assert "ref" not in checkout.get("with", {})
