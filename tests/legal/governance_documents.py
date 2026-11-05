"""
Reading the governance documents (docs/security, docs/operations): their
Markdown tables, sections, backticked paths and relative links, for the
tests that keep them true.
"""

import re
from pathlib import Path

REPOSITORY: Path = Path(__file__).resolve().parents[2]
OPERATIONS: Path = REPOSITORY / "docs" / "operations"
# A path in backticks: a folder ("app/use_cases/tools/") or a file.
PATH_IN_BACKTICKS: re.Pattern[str] = re.compile(r"`((?:[\w.-]+/)+[\w.-]*)`")
# [text](target) with a relative target; anchors and external links aside.
RELATIVE_LINK: re.Pattern[str] = re.compile(r"\]\((?!https?://|mailto:|#)([^)\s]+)\)")
SEPARATOR_ROW: re.Pattern[str] = re.compile(r"^\|(\s*:?-{3,}:?\s*\|)+$")


def read(relative_path: str) -> str:
    return (REPOSITORY / relative_path).read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """The text under `## heading` up to the next heading of that level."""

    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert match is not None, f"no section {heading!r}"
    return match.group(1)


def table_rows(text: str) -> list[list[str]]:
    """The body rows of every table in `text`, each as its stripped cells."""

    rows: list[list[str]] = []
    lines: list[str] = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("|") or SEPARATOR_ROW.match(line):
            continue
        is_header: bool = index + 1 < len(lines) and bool(
            SEPARATOR_ROW.match(lines[index + 1])
        )
        if not is_header:
            rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def missing_paths(text: str, *bases: Path) -> list[str]:
    """Backticked paths found under none of the repository and `bases`."""

    roots: tuple[Path, ...] = (REPOSITORY, *bases)
    return sorted(
        path
        for path in set(PATH_IN_BACKTICKS.findall(text))
        if not any((root / path).exists() for root in roots)
    )


def broken_links(document: Path) -> list[str]:
    """Relative links of `document` that lead to no file."""

    text: str = document.read_text(encoding="utf-8")
    return sorted(
        target
        for target in RELATIVE_LINK.findall(text)
        if ":" not in target
        and not (document.parent / target.split("#", 1)[0]).exists()
    )
