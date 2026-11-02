"""
The environments of the settings check (scripts/repository_environments.py,
judged by scripts/check_repository_settings.py): `production-release` exists,
only its expected reviewers approve and only `main` may use it; an
environment without a reviewer expectation needs no approval but keeps its
branch rule; a token that cannot read environments proves nothing.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.check_repository_settings import (
    EXIT_AS_EXPECTED,
    EXIT_SETTING_OFF,
    EXIT_UNUSABLE,
)
from tests.platform.test_repository_settings import EXPECTED, Answer, run

SETTINGS: Path = Path(__file__).resolve().parents[2] / ".github"
RELEASE: str = "production-release"
DRILL: str = "backup-drill"
ENVIRONMENTS: dict[str, Any] = {
    RELEASE: {"required_reviewers": ["owner"], "deployment_branches": ["main"]},
    DRILL: {"required_reviewers": [], "deployment_branches": ["main"]},
}
WITH_ENVIRONMENTS: dict[str, Any] = {**EXPECTED, "environments": ENVIRONMENTS}
CUSTOM_POLICY: dict[str, bool] = {
    "protected_branches": False,
    "custom_branch_policies": True,
}


def reviewers(*logins: str) -> dict[str, Any]:
    return {
        "type": "required_reviewers",
        "prevent_self_review": False,
        "reviewers": [
            {"type": "User", "reviewer": {"login": login, "id": 1}} for login in logins
        ],
    }


def environment(
    name: str, rules: list[dict[str, Any]], policy: object = CUSTOM_POLICY
) -> dict[str, Any]:
    return {
        "name": name,
        "can_admins_bypass": True,
        "protection_rules": [*rules, {"type": "branch_policy"}],
        "deployment_branch_policy": policy,
    }


def policies(*refs: tuple[str, str]) -> dict[str, Any]:
    return {
        "total_count": len(refs),
        "branch_policies": [{"name": name, "type": kind} for name, kind in refs],
    }


MAIN_ONLY: Answer = (200, policies(("main", "branch")))
PROTECTED: dict[str, Answer] = {
    f"environment-{RELEASE}": (200, environment(RELEASE, [reviewers("owner")])),
    f"branch-policies-{RELEASE}": MAIN_ONLY,
    f"environment-{DRILL}": (200, environment(DRILL, [])),
    f"branch-policies-{DRILL}": MAIN_ONLY,
}


def check(
    tmp_path: Path, changes: dict[str, Answer] | None = None
) -> tuple[int, str, str, str]:
    return run(tmp_path, PROTECTED | (changes or {}), expected=WITH_ENVIRONMENTS)


def test_protected_environments_as_expected_pass(tmp_path: Path) -> None:
    code, output, _, summary = check(tmp_path)

    assert code == EXIT_AS_EXPECTED, output
    assert f"environments ({RELEASE}, {DRILL})" in summary


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        (
            {f"environment-{RELEASE}": (404, {"message": "Not Found"})},
            f"{RELEASE}: the environment does not exist",
        ),
        (
            {f"environment-{RELEASE}": (200, environment(RELEASE, []))},
            f"{RELEASE}: no required reviewers (its jobs run without approval)",
        ),
        (
            {
                f"environment-{RELEASE}": (
                    200,
                    environment(RELEASE, [reviewers("owner", "intern")]),
                )
            },
            f"{RELEASE}: required reviewers are intern, owner, expected owner",
        ),
        (
            {
                f"environment-{RELEASE}": (
                    200,
                    environment(RELEASE, [reviewers("owner")], None),
                )
            },
            f"{RELEASE}: every branch may use it, expected only main",
        ),
        (
            {
                f"environment-{DRILL}": (
                    200,
                    environment(
                        DRILL,
                        [],
                        {"protected_branches": True, "custom_branch_policies": False},
                    ),
                )
            },
            f"{DRILL}: every protected branch may use it, expected only main",
        ),
        (
            {
                f"branch-policies-{DRILL}": (
                    200,
                    policies(("main", "branch"), ("feature/*", "branch")),
                )
            },
            f"{DRILL}: other branches may use it: feature/*",
        ),
        (
            {f"branch-policies-{RELEASE}": (200, policies(("v*", "tag")))},
            f"{RELEASE}: tags may use it: v*",
        ),
    ],
)
def test_every_weakened_environment_is_named(
    tmp_path: Path, changes: dict[str, Answer], problem: str
) -> None:
    code, output, _, summary = check(tmp_path, changes)

    assert code == EXIT_SETTING_OFF
    assert f"::error::Repository setting off: {problem}" in output
    assert f"- {problem}" in summary


def test_a_branch_left_out_of_the_policy_is_named(tmp_path: Path) -> None:
    code, output, _, _ = check(
        tmp_path, {f"branch-policies-{RELEASE}": (200, policies())}
    )

    assert code == EXIT_SETTING_OFF
    assert f"{RELEASE}: main may not use it" in output


def test_an_environment_without_reviewers_expected_needs_none(tmp_path: Path) -> None:
    code, _, _, _ = check(
        tmp_path,
        {f"environment-{DRILL}": (200, environment(DRILL, [reviewers("someone")]))},
    )

    assert code == EXIT_AS_EXPECTED


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        (
            {f"environment-{RELEASE}": (403, {"message": "Resource not accessible"})},
            "it needs Actions: read",
        ),
        (
            {f"branch-policies-{DRILL}": (403, {"message": "Resource not accessible"})},
            "it needs Actions: read",
        ),
        (
            {f"environment-{DRILL}": (401, {"message": "Bad credentials"})},
            "missing, expired or revoked",
        ),
    ],
)
def test_a_token_that_cannot_read_environments_proves_nothing(
    tmp_path: Path, changes: dict[str, Answer], reason: str
) -> None:
    code, _, errors, summary = check(tmp_path, changes)

    assert (code, summary) == (EXIT_UNUSABLE, "")
    assert reason in errors


def test_a_missing_environment_answer_proves_nothing(tmp_path: Path) -> None:
    code, _, errors, _ = run(
        tmp_path,
        PROTECTED,
        expected=WITH_ENVIRONMENTS,
        omit=(f"branch-policies-{RELEASE}",),
    )

    assert code == EXIT_UNUSABLE
    assert f"branch-policies-{RELEASE}.http: no answer saved" in errors


@pytest.mark.parametrize(
    "environments",
    [
        {RELEASE: {"required_reviewers": "owner", "deployment_branches": []}},
        {RELEASE: {"required_reviewers": [""], "deployment_branches": []}},
        {RELEASE: {"required_reviewers": [], "deployment_branches": None}},
    ],
)
def test_unusable_environment_expectations_are_refused(
    tmp_path: Path, environments: dict[str, Any]
) -> None:
    code, _, errors, _ = run(
        tmp_path, expected={**EXPECTED, "environments": environments}
    )

    assert code == EXIT_UNUSABLE
    assert "lists names" in errors


def test_the_release_needs_a_person_and_both_environments_only_main() -> None:
    expected = json.loads(
        (SETTINGS / "repository-settings.json").read_text(encoding="utf-8")
    )
    environments = expected["environments"]

    assert set(environments) == {RELEASE, DRILL}
    assert environments[RELEASE]["required_reviewers"]
    for name in (RELEASE, DRILL):
        assert environments[name]["deployment_branches"] == ["main"], name
    # Every reviewer may approve production: the code owner, nobody else.
    owners = (SETTINGS / "CODEOWNERS").read_text(encoding="utf-8")
    for reviewer in environments[RELEASE]["required_reviewers"]:
        assert f"@{reviewer}" in owners
