"""
Write the generated parts of the DPA into every translation
(docs/legal/dpa-*.md), between their markers: section 8's sub-processor
table from the sub-processor registry (every version: the API serves the
live list anyway) and section 9's security measures from the security
measure registry, as the file's own version lists them:

    uv run python -m scripts.render_subprocessor_table

With `--check` nothing is written; the exit status is 1 when a file is out
of date (tests/legal runs the same comparison). A part without its markers
is left alone (the DPA versions before 2026-10-06 have no generated
section 9).
"""

import sys
from pathlib import Path

from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
    DPA_FILE_PATTERN,
)
from app.registries.legal.security_measure_registry import SecurityMeasureRegistry
from app.registries.legal.subprocessor_registry import SubprocessorRegistry
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.utilities.legal.security_measures_section import (
    find_security_block,
    render_security_measures,
    write_security_block,
)
from app.utilities.legal.subprocessor_table import (
    find_table_block,
    render_subprocessor_table,
    write_table_block,
)
from app.utilities.localization.language_tags import parse_language_tag


def rendered(text: str, version: str, language: str) -> str:
    """The file's text with both generated parts as the registries make them."""

    tag = parse_language_tag(language)
    if find_table_block(text) is not None:
        entries = SubprocessorRegistry().list_entries()
        text = write_table_block(text, render_subprocessor_table(entries, tag))
    if find_security_block(text) is not None:
        measures = SecurityMeasureRegistry().measures_of(DpaDocumentVersion(version))
        text = write_security_block(text, render_security_measures(measures, tag))
    return text


def render_files(directory: Path, write: bool) -> list[Path]:
    """The DPA files whose generated parts differ (rewritten if `write`)."""

    stale: list[Path] = []
    for path in sorted(directory.glob("dpa-*.md")):
        match = DPA_FILE_PATTERN.match(path.name)
        if match is None:
            continue

        text: str = path.read_text(encoding="utf-8")
        expected: str = rendered(text, match.group("version"), match.group("language"))
        if expected == text:
            continue

        stale.append(path)
        if write:
            path.write_text(expected, encoding="utf-8")

    return stale


def main(arguments: list[str]) -> int:
    check_only: bool = "--check" in arguments
    stale: list[Path] = render_files(DEFAULT_LEGAL_DOCUMENTS_DIRECTORY, not check_only)
    for path in stale:
        verb: str = "out of date" if check_only else "updated"
        sys.stdout.write(f"{path.name}: {verb}\n")

    return 1 if check_only and stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
