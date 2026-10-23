"""
The repository settings check (scripts/check_repository_settings.py, run by
.github/workflows/repo-settings.yml): branch protection from either its
classic rule or a ruleset, private vulnerability reporting and Dependabot
security updates, judged from saved `gh api --include` answers.
"""

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

import pytest

from scripts.check_repository_settings import (
    EXIT_AS_EXPECTED,
    EXIT_SETTING_OFF,
    EXIT_UNUSABLE,
    main,
)
from scripts.repository_settings import SettingsError, parse_response

CHECKS: list[str] = ["Backend checks", "End-to-end (1/9)"]
MAIN: dict[str, Any] = {
    "pull_request_required": True,
    "required_approving_review_count": 0,
    "required_status_checks": CHECKS,
    "force_pushes_blocked": True,
    "deletions_blocked": True,
}
EXPECTED: dict[str, Any] = {
    "branches": {"main": MAIN},
    "private_vulnerability_reporting": True,
    "dependabot_security_updates": True,
}
CLASSIC: dict[str, Any] = {
    "required_status_checks": {
        "strict": False,
        "contexts": ["Backend checks"],
        "checks": [{"context": "End-to-end (1/9)", "app_id": 15368}],
    },
    "required_pull_request_reviews": {"required_approving_review_count": 0},
    "allow_force_pushes": {"enabled": False},
    "allow_deletions": {"enabled": False},
}
RULES: list[dict[str, Any]] = [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "pull_request", "parameters": {"required_approving_review_count": 1}},
    {
        "type": "required_status_checks",
        "parameters": {
            "required_status_checks": [{"context": check} for check in CHECKS]
        },
    },
]
NOT_PROTECTED: tuple[int, object] = (404, {"message": "Branch not protected"})


def http(status: int, body: object) -> str:
    reason = {200: "OK", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found"}
    return (
        f"HTTP/2.0 {status} {reason[status]}\r\nContent-Type: application/json\r\n"
        f"X-Github-Media-Type: github.v3\r\n\r\n{json.dumps(body)}"
    )


Answer = tuple[int, object]
DEFAULT_ANSWERS: dict[str, Answer] = {
    "protection-main": (200, CLASSIC),
    "rules-main": (200, []),
    "reporting": (200, {"enabled": True}),
    "security-fixes": (200, {"enabled": True, "paused": False}),
}


def run(
    tmp_path: Path,
    answers: dict[str, Answer] | None = None,
    *,
    expected: object = EXPECTED,
    omit: tuple[str, ...] = (),
) -> tuple[int, str, str, str]:
    responses = tmp_path / "settings"
    responses.mkdir(exist_ok=True)
    for name, (status, body) in (DEFAULT_ANSWERS | (answers or {})).items():
        if name not in omit:
            path = responses / f"{name}.http"
            path.write_text(http(status, body), encoding="utf-8")
    expected_path = tmp_path / "repository-settings.json"
    expected_path.write_text(json.dumps(expected), encoding="utf-8")
    summary = tmp_path / "summary.md"
    output, errors = io.StringIO(), io.StringIO()
    arguments = ["--expected", str(expected_path), "--responses", str(responses)]
    with redirect_stdout(output), redirect_stderr(errors):
        code = main([*arguments, "--summary", str(summary)])
    text = summary.read_text(encoding="utf-8") if summary.exists() else ""
    return code, output.getvalue(), errors.getvalue(), text


def test_gh_answers_are_read_with_their_status() -> None:
    assert parse_response(http(404, {"message": "Not Found"})).status == 404
    lf = parse_response('HTTP/1.1 200 OK\nContent-Type: x\n\n{"enabled": true}')
    assert (lf.status, lf.body) == (200, {"enabled": True})
    with pytest.raises(SettingsError, match="no HTTP status line"):
        parse_response("")
    with pytest.raises(SettingsError, match="not JSON"):
        parse_response("HTTP/2.0 200 OK\r\n\r\n<html>")


def test_classic_protection_as_expected_passes(tmp_path: Path) -> None:
    code, output, _, summary = run(tmp_path)

    assert code == EXIT_AS_EXPECTED
    assert "::error::" not in output
    assert summary.startswith("## Repository settings: as expected")


def test_a_ruleset_alone_protects_the_branch(tmp_path: Path) -> None:
    code, _, _, _ = run(
        tmp_path, {"protection-main": NOT_PROTECTED, "rules-main": (200, RULES)}
    )

    assert code == EXIT_AS_EXPECTED


def test_classic_protection_and_rulesets_add_up(tmp_path: Path) -> None:
    classic = {**CLASSIC, "required_status_checks": {"contexts": ["Backend checks"]}}
    some_rules = [RULES[0], RULES[3]]
    answers: dict[str, Answer] = {
        "protection-main": (200, classic),
        "rules-main": (200, some_rules),
    }
    code, _, _, _ = run(tmp_path, answers)

    assert code == EXIT_AS_EXPECTED


def test_an_unprotected_branch_fails(tmp_path: Path) -> None:
    code, output, _, summary = run(tmp_path, {"protection-main": NOT_PROTECTED})

    assert code == EXIT_SETTING_OFF
    assert "::error::Repository setting off: main: not protected" in output
    assert summary.startswith("## Repository settings: 1 setting(s) off")


def test_every_weakened_rule_is_named(tmp_path: Path) -> None:
    weak = {
        "required_status_checks": {"contexts": ["Backend checks"]},
        "allow_force_pushes": {"enabled": True},
        "allow_deletions": {"enabled": True},
    }
    strict = {**MAIN, "required_approving_review_count": 1}
    code, output, _, _ = run(
        tmp_path,
        {"protection-main": (200, weak)},
        expected={**EXPECTED, "branches": {"main": strict}},
    )

    assert code == EXIT_SETTING_OFF
    for problem in [
        "main: commits can be pushed without a pull request",
        "main: 0 approving review(s) required, 1 expected",
        "main: required checks missing: End-to-end (1/9)",
        "main: force pushes are allowed",
        "main: the branch can be deleted",
    ]:
        assert f"::error::Repository setting off: {problem}" in output


@pytest.mark.parametrize(
    ("answers", "problem"),
    [
        (
            {"reporting": (200, {"enabled": False})},
            "private vulnerability reporting is off",
        ),
        (
            {"security-fixes": (404, {"message": "Not Found"})},
            "security updates are off",
        ),
        ({"security-fixes": (200, {"enabled": True, "paused": True})}, "are paused"),
    ],
)
def test_reporting_and_security_updates_must_stay_on(
    tmp_path: Path, answers: dict[str, Answer], problem: str
) -> None:
    code, output, _, _ = run(tmp_path, answers)

    assert code == EXIT_SETTING_OFF
    assert problem in output


@pytest.mark.parametrize(
    ("answers", "reason"),
    [
        (
            {"protection-main": (401, {"message": "Bad credentials"})},
            "missing, expired or revoked",
        ),
        (
            {"rules-main": (403, {"message": "Resource not accessible"})},
            "Administration: read",
        ),
        ({"protection-main": (404, {"message": "Not Found"})}, "HTTP 404 Not Found"),
        ({"reporting": (404, {"message": "Not Found"})}, "HTTP 404 Not Found"),
    ],
)
def test_a_token_that_cannot_read_the_settings_proves_nothing(
    tmp_path: Path, answers: dict[str, Answer], reason: str
) -> None:
    code, _, errors, summary = run(tmp_path, answers)

    assert (code, summary) == (EXIT_UNUSABLE, "")
    assert "::error::Repository settings check:" in errors
    assert reason in errors


def test_a_missing_answer_proves_nothing(tmp_path: Path) -> None:
    code, _, errors, _ = run(tmp_path, omit=("reporting",))

    assert code == EXIT_UNUSABLE
    assert "reporting.http: no answer saved" in errors


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"branches": {}}, "no branch is expected"),
        ({"private_vulnerability_reporting": "yes"}, "must be true or false"),
        ({"dependabot_security_updates": None}, "must be true or false"),
    ],
)
def test_unusable_expectations_are_refused(
    tmp_path: Path, change: dict[str, object], problem: str
) -> None:
    code, _, errors, _ = run(tmp_path, expected={**EXPECTED, **change})

    assert code == EXIT_UNUSABLE
    assert problem in errors


def test_a_branch_expectation_names_its_checks(tmp_path: Path) -> None:
    branch: dict[str, Any] = {**MAIN, "required_status_checks": []}
    code, _, errors, _ = run(
        tmp_path, expected={**EXPECTED, "branches": {"main": branch}}
    )

    assert code == EXIT_UNUSABLE
    assert "required_status_checks lists the checks" in errors
