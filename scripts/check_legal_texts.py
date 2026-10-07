"""
Release check of the legal texts in force: counts the fields in square
brackets still to be filled in (operator details, locations, periods) in the
DPA version of DPA_DOCUMENT_VERSION and the terms, privacy policy and cookie
statement in force today, in every language:

    uv run python -m scripts.check_legal_texts

While LEGAL_TEXTS_FINAL is off the texts are drafts: the counts are printed
and the check passes. With LEGAL_TEXTS_FINAL=true (the operator's lawyer has
reviewed and completed them) any remaining field fails the check.
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
    DPA_FILE_PATTERN,
)
from app.registries.legal.legal_text_registry import LEGAL_TEXT_FILE_PATTERN
from app.utilities.config_helpers.app_settings.compliance_settings_section import (
    DEFAULT_DPA_DOCUMENT_VERSION,
)
from app.utilities.legal.legal_text_fingerprints import count_placeholders

TRUE_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})


def texts_in_force(directory: Path, dpa_version: str, today: str) -> list[Path]:
    """The DPA version's files and the latest terms/privacy/cookies by `today`."""

    chosen: list[Path] = []
    latest: dict[str, str] = {}
    for path in sorted(directory.glob("*.md")):
        dpa = DPA_FILE_PATTERN.match(path.name)
        if dpa is not None:
            if dpa.group("version") == dpa_version:
                chosen.append(path)
            continue

        text = LEGAL_TEXT_FILE_PATTERN.match(path.name)
        if text is not None and text.group("version") <= today:
            kind: str = text.group("kind")
            latest[kind] = max(latest.get(kind, ""), text.group("version"))

    for path in sorted(directory.glob("*.md")):
        text = LEGAL_TEXT_FILE_PATTERN.match(path.name)
        if text is not None and latest.get(text.group("kind")) == text.group("version"):
            chosen.append(path)
    return chosen


def main(
    environment: dict[str, str],
    directory: Path = DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
    today: str | None = None,
) -> int:
    is_final: bool = environment.get("LEGAL_TEXTS_FINAL", "").strip().lower() in (
        TRUE_VALUES
    )
    dpa_version: str = environment.get("DPA_DOCUMENT_VERSION") or (
        DEFAULT_DPA_DOCUMENT_VERSION
    )
    day: str = today or datetime.now(UTC).date().isoformat()
    total: int = 0
    for path in texts_in_force(directory, dpa_version, day):
        count: int = count_placeholders(path.read_text(encoding="utf-8"))
        total += count
        sys.stdout.write(f"{path.name}: {count} field(s) in square brackets\n")

    if is_final and total > 0:
        sys.stdout.write(
            f"LEGAL_TEXTS_FINAL is on, but {total} field(s) are still to be "
            "filled in.\n"
        )
        return 1

    state: str = "final" if is_final else "drafts (LEGAL_TEXTS_FINAL is off)"
    sys.stdout.write(f"Legal texts: {state}; {total} field(s) to fill in.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(dict(os.environ)))
