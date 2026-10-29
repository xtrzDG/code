"""
The scheduled check of .github/workflows/repo-settings.yml: the answers of
`gh api --include` it saved (scripts/repository_settings.py names the
files) against the reviewed expectations:

    uv run --no-project python -m scripts.check_repository_settings \\
        --expected .github/repository-settings.json \\
        --responses "$RUNNER_TEMP/settings" --summary "$GITHUB_STEP_SUMMARY"

Prints one GitHub error line per setting that is off and appends a short
Markdown report to the summary file. Exit codes: 0 every setting as
expected, 1 a setting is off (branch protection weakened or removed,
private vulnerability reporting or Dependabot security updates switched
off), 2 the check proves nothing (expectations unreadable, an answer
missing, a token that is missing, expired or may not read the settings).
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from scripts.repository_settings import (
    Expectations,
    Response,
    SettingsError,
    branch_problems,
    classic_protection,
    combined,
    parse_expectations,
    parse_response,
    reporting_problems,
    ruleset_protection,
    security_fixes_problems,
)

EXIT_AS_EXPECTED: int = 0
EXIT_SETTING_OFF: int = 1
EXIT_UNUSABLE: int = 2


def read_response(directory: Path, name: str) -> Response:
    path = directory / f"{name}.http"
    try:
        return parse_response(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SettingsError(
            f"{path.name}: no answer saved ({error.strerror})"
        ) from error
    except SettingsError as error:
        raise SettingsError(f"{path.name}: {error}") from error


def problems_of(expected: Expectations, responses: Path) -> list[str]:
    problems: list[str] = []
    for branch in expected.branches:
        protection = combined(
            classic_protection(
                branch.branch, read_response(responses, f"protection-{branch.branch}")
            ),
            ruleset_protection(
                branch.branch, read_response(responses, f"rules-{branch.branch}")
            ),
        )
        problems += branch_problems(branch, protection)
    problems += reporting_problems(expected, read_response(responses, "reporting"))
    problems += security_fixes_problems(
        expected, read_response(responses, "security-fixes")
    )
    return problems


def report(expected: Expectations, problems: list[str]) -> list[str]:
    branches = ", ".join(branch.branch for branch in expected.branches)
    if not problems:
        return [
            "## Repository settings: as expected",
            "",
            f"Protection of {branches}, private vulnerability reporting and"
            " Dependabot security updates match .github/repository-settings.json.",
        ]
    return [
        f"## Repository settings: {len(problems)} setting(s) off",
        "",
        *(f"- {problem}" for problem in problems),
        "",
        "Restore them in the repository's settings (SECURITY.md,"
        ' "Repository settings"); change .github/repository-settings.json'
        " only with a reviewed reason.",
    ]


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Repository settings against their reviewed expectations."
    )
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parsed = parser.parse_args(arguments)

    try:
        expected = parse_expectations(parsed.expected.read_text(encoding="utf-8"))
        problems = problems_of(expected, parsed.responses)
    except (OSError, SettingsError, TypeError, ValueError) as error:
        print(f"::error::Repository settings check: {error}", file=sys.stderr)
        return EXIT_UNUSABLE

    for problem in problems:
        print(f"::error::Repository setting off: {problem}")
    if not problems:
        print("Every repository setting is as expected.")
    if parsed.summary is not None:
        with parsed.summary.open("a", encoding="utf-8") as summary:
            summary.write("\n".join(report(expected, problems)) + "\n")
    return EXIT_SETTING_OFF if problems else EXIT_AS_EXPECTED


if __name__ == "__main__":
    sys.exit(main())
