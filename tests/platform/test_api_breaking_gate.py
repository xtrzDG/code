"""
The oasdiff gate of the API description (docs/api-versioning.md): it runs
on every pull request unless the `api-breaking` label lets a deliberate
break through, it treats a changed operationId (a renamed SDK method) as an
error, and a **Breaking** entry of docs/API_CHANGELOG.md names that label
and the migration path of its clients.
"""

import re
from pathlib import Path
from typing import Any, cast

import yaml

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
WORKFLOW: Path = PROJECT_ROOT / ".github" / "workflows" / "api-contract.yml"
SEVERITY_LEVELS: Path = PROJECT_ROOT / ".github" / "oasdiff-severity-levels.txt"
CHANGELOG: Path = PROJECT_ROOT / "docs" / "API_CHANGELOG.md"
BREAKING_LABEL: str = "api-breaking"
ENTRY_SPLIT: re.Pattern[str] = re.compile(r"^## ", re.MULTILINE)


def breaking_job() -> dict[str, Any]:
    workflow = cast(dict[str, Any], yaml.safe_load(WORKFLOW.read_text("utf-8")))
    return cast(dict[str, Any], workflow["jobs"]["breaking-changes"])


def test_the_label_alone_lets_a_breaking_change_through() -> None:
    workflow = cast(dict[str, Any], yaml.safe_load(WORKFLOW.read_text("utf-8")))
    # PyYAML reads the bare `on:` key as True.
    triggers = cast(dict[str, Any], workflow[True])["pull_request"]["types"]

    assert breaking_job()["if"] == (
        "${{ !contains(github.event.pull_request.labels.*.name, "
        f"'{BREAKING_LABEL}') }}}}"
    )
    assert {"labeled", "unlabeled"} <= set(triggers)


def test_the_gate_fails_on_errors_with_our_severity_levels() -> None:
    commands: str = "\n".join(
        str(step.get("run", "")) for step in breaking_job()["steps"]
    )

    assert 'oasdiff" breaking' in commands
    assert "--fail-on ERR" in commands
    assert "--severity-levels .github/oasdiff-severity-levels.txt" in commands


def test_a_changed_operation_id_is_an_error() -> None:
    levels: dict[str, str] = dict(
        line.split() for line in SEVERITY_LEVELS.read_text("utf-8").splitlines()
    )

    assert levels == {"api-operation-id-removed": "err"}


def test_the_newest_breaking_entry_names_the_label_and_a_migration_path() -> None:
    # Entries are newest first; older breaks predate the rule.
    entries: list[str] = ENTRY_SPLIT.split(CHANGELOG.read_text("utf-8"))[1:]
    newest: str = next(entry for entry in entries if "**Breaking**" in entry)

    assert f"`{BREAKING_LABEL}`" in newest
    assert "Migration:" in newest
