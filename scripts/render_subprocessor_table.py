"""
Write the DPA's section 8 sub-processor table from the registry into every
translation (docs/legal/dpa-*.md), between its two markers:

    uv run python -m scripts.render_subprocessor_table

With `--check` nothing is written; the exit status is 1 when a file is out
of date (tests/legal runs the same comparison). A DPA file without the
markers is left alone.
"""

import sys
from pathlib import Path

from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
    DPA_FILE_PATTERN,
)
from app.registries.legal.subprocessor_registry import SubprocessorRegistry
from app.utilities.legal.subprocessor_table import (
    find_table_block,
    render_subprocessor_table,
    write_table_block,
)
from app.utilities.localization.language_tags import parse_language_tag


def render_files(directory: Path, write: bool) -> list[Path]:
    """The DPA files whose table differs from the registry (rewritten if `write`)."""

    entries = SubprocessorRegistry().list_entries()
    stale: list[Path] = []
    for path in sorted(directory.glob("dpa-*.md")):
        match = DPA_FILE_PATTERN.match(path.name)
        text: str = path.read_text(encoding="utf-8")
        if match is None or find_table_block(text) is None:
            continue

        table: str = render_subprocessor_table(
            entries, parse_language_tag(match.group("language"))
        )
        if find_table_block(text) == table:
            continue

        stale.append(path)
        if write:
            path.write_text(write_table_block(text, table), encoding="utf-8")

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
