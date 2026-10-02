"""CI workflows stay hardened: pinned actions, least privilege, checked tools.

A tag (`@v4`) can be moved to other code by whoever controls the action's
repository; a commit SHA cannot. Dependabot keeps the pins current and the
comment names the release.
"""

import re
from pathlib import Path

import pytest

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
WORKFLOW_DIRECTORY: Path = PROJECT_ROOT / ".github" / "workflows"
USES_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*(?:-\s+)?uses:\s*(?P<target>\S+)(?P<rest>.*)$"
)
PINNED_PATTERN: re.Pattern[str] = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
VERSION_COMMENT_PATTERN: re.Pattern[str] = re.compile(r"^\s+#\s+v\d+(\.\d+)*\s*$")
DOWNLOAD_PATTERN: re.Pattern[str] = re.compile(r"https://\S+/releases/download/")


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


def test_dependabot_watches_every_ecosystem() -> None:
    text: str = (PROJECT_ROOT / ".github" / "dependabot.yml").read_text(
        encoding="utf-8"
    )
    ecosystems = set(re.findall(r"package-ecosystem:\s*(\S+)", text))

    assert ecosystems == {"uv", "npm", "github-actions", "docker"}
    assert text.count("interval: weekly") == len(ecosystems)
