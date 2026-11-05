"""
The registry check of new dependencies as CI runs it (SDLC-02,
scripts/dependency_registry_review.py, step "New dependencies on their
registries" of the job "security"): the report in the run summary, a
failing signal fails the step unless a reviewed exception accepts it with a
reason, and nothing measured is never a pass. GitHub's dependency review
puts its summary on the pull request. The registries are fakes.
"""

import datetime
from pathlib import Path

import pytest
import yaml

from scripts.dependency_registry.manifests import NPM, PYPI, Dependency
from scripts.dependency_registry.registry_facts import registry_address
from scripts.dependency_registry_review import (
    EXIT_FAILED,
    EXIT_PASSED,
    EXIT_UNUSABLE,
    main,
    reviewed_exceptions,
)
from tests.platform.dependency_registry_fixtures import (
    NOW_ISO,
    NPM_FRESH,
    NPM_WELL_KEPT,
    PYPI_WELL_KEPT,
    FakeRegistry,
    write_manifests,
)
from tests.platform.environment_sources import ROOT
from tests.platform.test_supply_chain_workflows import steps, workflow

NOW: datetime.datetime = datetime.datetime.fromisoformat(NOW_ISO)
LEFT_TRIM = Dependency(NPM, "left-trim", "web/package.json")
FRESH = Dependency(NPM, "fresh-helper", "web/package.json")
TIDY = Dependency(PYPI, "tidy", "pyproject.toml")
REGISTRY: dict[str, dict[str, object]] = {
    registry_address(LEFT_TRIM): NPM_WELL_KEPT,
    registry_address(FRESH): NPM_FRESH,
    registry_address(TIDY): PYPI_WELL_KEPT,
}


def run(
    tmp_path: Path,
    added_npm: dict[str, str],
    *,
    reviewed: str = "[reviewed]\n",
    registry: FakeRegistry | None = None,
) -> tuple[int, str]:
    base = write_manifests(tmp_path / "base", {"react": "19"}, ["fastapi"])
    head = write_manifests(
        tmp_path / "head", {"react": "19", **added_npm}, ["fastapi", "tidy"]
    )
    (tmp_path / "reviewed.toml").write_text(reviewed, encoding="utf-8")
    summary = tmp_path / "summary.md"
    status = main(
        [
            "--base",
            str(base),
            "--head",
            str(head),
            "--reviewed",
            str(tmp_path / "reviewed.toml"),
            "--summary",
            str(summary),
        ],
        fetch=registry or FakeRegistry(REGISTRY),
        now=NOW,
    )
    return status, summary.read_text("utf-8") if summary.exists() else ""


def test_well_kept_new_dependencies_pass_with_their_measured_facts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status, summary = run(tmp_path, {"left-trim": "2"})

    assert status == EXIT_PASSED
    assert (
        "| npm:left-trim | `web/package.json` | 2024-10-01 | 2026-10-02 | 3" in summary
    )
    assert (
        "| pypi:tidy | `pyproject.toml` | 2020-05-01 | 2026-09-01 | 2 | no | no"
        in summary
    )
    assert "::error" not in capsys.readouterr().out


def test_a_failing_signal_fails_the_step_with_annotations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status, summary = run(tmp_path, {"fresh-helper": "0.0.2"})
    out = capsys.readouterr().out

    assert status == EXIT_FAILED
    assert (
        "- npm:fresh-helper: too-new, first released 9 days ago: **fails**" in summary
    )
    assert (
        "- npm:fresh-helper: install-code, installing it runs its own code: warn"
        in summary
    )
    assert (
        "::error file=web/package.json,title=New dependency npm:fresh-helper::too-new"
        in out
    )
    assert (
        "::warning file=web/package.json,title=New dependency npm:fresh-helper::" in out
    )
    assert (
        "accept each with its reason in .github/dependency-registry-review.toml" in out
    )


def test_an_accepted_signal_passes_and_the_report_keeps_the_reason(
    tmp_path: Path,
) -> None:
    reviewed = (
        '[reviewed."npm:fresh-helper"]\nsignals = ["too-new"]\n'
        'reason = "Our vendor\'s SDK, released with its new API."\n'
    )

    status, summary = run(tmp_path, {"fresh-helper": "0.0.2"}, reviewed=reviewed)

    assert status == EXIT_PASSED
    assert (
        "too-new, first released 9 days ago: fail (accepted: Our vendor's SDK"
        in summary
    )


def test_a_name_the_registry_does_not_know_fails(tmp_path: Path) -> None:
    status, summary = run(tmp_path, {"left-trim-utils-x": "1"})

    assert status == EXIT_FAILED
    assert (
        "| npm:left-trim-utils-x | `web/package.json` | not on the registry |"
        in summary
    )
    assert "not-found" in summary


@pytest.mark.parametrize(
    "reviewed",
    [
        '[reviewed."npm:fresh-helper"]\nsignals = ["too-new"]\n',
        '[reviewed."npm:fresh-helper"]\nsignals = []\nreason = "x"\n',
        "[reviewed\n",
    ],
)
def test_an_exception_without_its_signals_and_reason_measures_nothing(
    tmp_path: Path, reviewed: str
) -> None:
    status, summary = run(tmp_path, {"fresh-helper": "0.0.2"}, reviewed=reviewed)

    assert status == EXIT_UNUSABLE
    assert summary == ""


def test_an_unreachable_registry_measures_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status, _ = run(
        tmp_path, {"left-trim": "2"}, registry=FakeRegistry(REGISTRY, status=503)
    )

    assert status == EXIT_UNUSABLE
    assert (
        "::error::The new dependencies could not be measured" in capsys.readouterr().out
    )


def test_no_new_dependency_asks_no_registry(tmp_path: Path) -> None:
    registry = FakeRegistry(REGISTRY)
    base = write_manifests(tmp_path / "base", {"react": "19"}, ["fastapi"])

    status = main(
        ["--base", str(base), "--head", str(base), "--summary", str(tmp_path / "s.md")],
        fetch=registry,
        now=NOW,
    )

    assert status == EXIT_PASSED
    assert registry.asked == []
    assert "adds no direct dependency" in (tmp_path / "s.md").read_text("utf-8")


def test_the_committed_exceptions_file_is_readable_and_empty() -> None:
    text = (ROOT / ".github" / "dependency-registry-review.toml").read_text("utf-8")

    assert "[reviewed]" in text
    assert reviewed_exceptions(text) == {}


def test_ci_measures_each_pull_request_s_new_dependencies_after_the_review() -> None:
    job = workflow("ci.yml")["jobs"]["security"]
    names = [str(step.get("name", "")) for step in steps(job)]
    step = steps(job)[names.index("New dependencies on their registries")]
    review = names.index("Dependencies this pull request changes (dependency review)")

    assert names.index("New dependencies on their registries") == review + 1
    assert step["if"] == "${{ !cancelled() && github.event_name == 'pull_request' }}"
    assert step["env"]["BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
    assert 'git worktree add --detach "$RUNNER_TEMP/base" "$BASE_SHA"' in step["run"]
    assert "python -m scripts.dependency_registry_review" in step["run"]
    assert '--summary "$GITHUB_STEP_SUMMARY"' in step["run"]
    assert "continue-on-error" not in step
    # The history the base commit is in, and the token that comments.
    assert steps(job)[0]["with"]["fetch-depth"] == 0
    assert job["permissions"] == {"contents": "read", "pull-requests": "write"}


def test_the_dependency_review_comments_its_summary_on_the_pull_request() -> None:
    config = yaml.safe_load(
        (ROOT / ".github" / "dependency-review-config.yml").read_text("utf-8")
    )

    assert config["comment-summary-in-pr"] == "always"
