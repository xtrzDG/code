"""
Record the schema snapshots and golden fixtures of the stored documents.

    uv run python -m tests.storage.document_evolution.refresh

For every collection of the catalog: writes the golden fixture of the
current version if it is missing (an existing fixture is never touched)
and the schema snapshot. Refuses, with exit code 1, a document type whose
shape changed without a `schema_version` bump, or whose version went down.
"""

import sys
from collections.abc import Sequence

from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from tests.storage.document_evolution.evolution_files import (
    REPOSITORY_FILES,
    EvolutionFiles,
)
from tests.storage.document_evolution.evolution_policy import DocumentEvolution


def refresh_all(files: EvolutionFiles = REPOSITORY_FILES) -> list[str]:
    """Refresh every catalog collection; the problems that stopped one."""

    problems: list[str] = []
    for definition in DOCUMENT_COLLECTIONS:
        problems.extend(
            DocumentEvolution(
                definition.name, definition.document_type, files
            ).refresh()
        )

    return problems


def main(arguments: Sequence[str] | None = None) -> int:
    del arguments
    problems: list[str] = refresh_all()
    for problem in problems:
        print(problem, file=sys.stderr)

    print(f"{len(DOCUMENT_COLLECTIONS)} collections, {len(problems)} refused.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
