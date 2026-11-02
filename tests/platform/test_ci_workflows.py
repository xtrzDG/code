"""CI workflows stay hardened: pinned actions, least privilege, checked tools.

A tag (`@v4`) can be moved to other code by whoever controls the action's
repository; a commit SHA cannot. Dependabot keeps the pins current and the
comment names the release. No checkout leaves the job's token in the
working copy, and a secret reaches only the step that uses it.
"""

import re
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
WORKFLOW_DIRECTORY: Path = PROJECT_ROOT / ".github" / "workflows"
USES_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*(?:-\s+)?uses:\s*(?P<target>\S+)(?P<rest>.*)$"
)
PINNED_PATTERN: re.Pattern[str] = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
VERSION_COMMENT_PATTERN: re.Pattern[str] = re.compile(r"^\s+#\s+v\d+(\.\d+)*\s*$")
# Release archives, prebuilt npm tarballs and wheels fetched outside a lockfile.
DOWNLOAD_PATTERN: re.Pattern[str] = re.compile(
    r"https://\S+/releases/download/|https://registry\.npmjs\.org/\S+/-/"
    r"|https://files\.pythonhosted\.org/"
)
SECRET_PATTERN: re.Pattern[str] = re.compile(r"\$\{\{\s*secrets\.")


def workflow_paths() -> list[Path]:
    return sorted(WORKFLOW_DIRECTORY.glob("*.yml"))


def test_there_are_workflows() -> None:
    names = {path.name for path in workflow_paths()}

    assert {"ci.yml", "codeql.yml", "api-contract.yml"} <= names


@pytest.mark.parametrize("workflow_path", workflow_paths(), ids=lambda path: path.name)
def test_every_action_is_pinned_to_a_commit_with_its_version(
    workflow_path: Path,
) -> None:
    unpinned: list[str] = []
    for line in workflow_path.read_text(encoding="utf-8").splitlines():
        match = USES_PATTERN.match(line)
        if match is None:
            continue

        target: str = match.group("target")
        if PINNED_PATTERN.match(target) is None or (
            VERSION_COMMENT_PATTERN.match(match.group("rest")) is None
        ):
            unpinned.append(line.strip())

    assert unpinned == [], (
        "Pin every action to a full commit SHA followed by '# vX.Y.Z':\n"
        + "\n".join(unpinned)
    )


@pytest.mark.parametrize("workflow_path", workflow_paths(), ids=lambda path: path.name)
def test_workflows_default_to_read_only_permissions(workflow_path: Path) -> None:
    text: str = workflow_path.read_text(encoding="utf-8")

    assert re.search(r"^permissions:\n  contents: read$", text, re.MULTILINE)
    assert "write-all" not in text
    assert "pull_request_target" not in text


@pytest.mark.parametrize("workflow_path", workflow_paths(), ids=lambda path: path.name)
def test_downloaded_tools_are_checked_against_a_digest(workflow_path: Path) -> None:
    text: str = workflow_path.read_text(encoding="utf-8")
    downloads: int = len(DOWNLOAD_PATTERN.findall(text))

    assert text.count("sha256sum --check") == downloads


def workflow(path: Path) -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def jobs(path: Path) -> dict[str, dict[str, Any]]:
    return cast(dict[str, dict[str, Any]], workflow(path)["jobs"])


@pytest.mark.parametrize("workflow_path", workflow_paths(), ids=lambda path: path.name)
def test_no_checkout_keeps_the_token(workflow_path: Path) -> None:
    kept = [
        f"{name}: {step['uses']}"
        for name, job in jobs(workflow_path).items()
        for step in cast(list[dict[str, Any]], job.get("steps", []))
        if str(step.get("uses", "")).startswith("actions/checkout@")
        and step.get("with", {}).get("persist-credentials") is not False
    ]

    assert kept == []


@pytest.mark.parametrize("workflow_path", workflow_paths(), ids=lambda path: path.name)
def test_secrets_reach_only_the_steps_that_use_them(workflow_path: Path) -> None:
    document = workflow(workflow_path)
    leaks = [
        f"{name}: env"
        for name, job in jobs(workflow_path).items()
        if SECRET_PATTERN.search(yaml.safe_dump(job.get("env", {})))
    ]
    if SECRET_PATTERN.search(yaml.safe_dump(document.get("env", {}))):
        leaks.append("workflow env")

    assert leaks == []


def test_dependabot_watches_every_ecosystem_with_a_week_of_cooldown() -> None:
    path = PROJECT_ROOT / ".github" / "dependabot.yml"
    updates = cast(list[dict[str, Any]], workflow(path)["updates"])
    ecosystems = {str(update["package-ecosystem"]) for update in updates}
    directories: set[str] = set()
    for update in updates:
        directories |= {str(update.get("directory", ""))} | set(
            update.get("directories", [])
        )

    assert ecosystems == {
        "uv",
        "npm",
        "pip",
        "github-actions",
        "docker",
        "docker-compose",
    }
    assert all(update["schedule"]["interval"] == "weekly" for update in updates)
    # A new release waits a week; security updates do not (Dependabot's rule).
    assert all(update["cooldown"]["default-days"] >= 7 for update in updates)
    for lockfile_directory in ("/web", "/integrations/zapier", "/.github/tools/lhci"):
        assert lockfile_directory in directories, lockfile_directory
    assert {"/.github/tools/pip-audit", "/perf"} <= directories
