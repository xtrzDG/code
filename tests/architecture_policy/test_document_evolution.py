"""
Stored document shapes evolve only with a schema_version bump and a golden
fixture of the new version (rules: docs/operations/deploys.md).

When this fails after a model change: bump the document's `schema_version`,
add an upcaster if old rows need one, then run
`uv run python -m tests.storage.document_evolution.refresh`, which records
the new shape and writes the new golden fixture (never touching old ones).
"""

from pathlib import Path

import pytest
from base_pydantic_schemas import PersistentDocument

from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from tests.storage.document_evolution.evolution_files import (
    GOLDEN_DIRECTORY,
    REPOSITORY_FILES,
    SCHEMA_DIRECTORY,
    EvolutionFiles,
    stored_shape,
)
from tests.storage.document_evolution.evolution_policy import (
    DocumentEvolution,
    SnapshotStatus,
)
from tests.storage.evolution_documents import (
    NOTES_COLLECTION,
    NoteV1,
    NoteV1Changed,
    NoteV1Described,
    NoteV2,
)

CASES: list[DocumentEvolution] = [
    DocumentEvolution(definition.name, definition.document_type, REPOSITORY_FILES)
    for definition in DOCUMENT_COLLECTIONS
]


@pytest.mark.parametrize("evolution", CASES, ids=lambda case: case.label)
def test_every_shape_change_comes_with_a_version_bump(
    evolution: DocumentEvolution,
) -> None:
    assert evolution.snapshot_problems() == []


@pytest.mark.parametrize("evolution", CASES, ids=lambda case: case.label)
def test_every_version_keeps_a_golden_fixture(evolution: DocumentEvolution) -> None:
    assert evolution.golden_problems() == []


def test_no_fixture_outlives_its_collection() -> None:
    names: set[str] = {str(definition.name) for definition in DOCUMENT_COLLECTIONS}
    types: set[str] = {
        f"{definition.document_type.__name__}.json"
        for definition in DOCUMENT_COLLECTIONS
    }

    assert {path.name for path in GOLDEN_DIRECTORY.iterdir()} == names
    assert {path.name for path in SCHEMA_DIRECTORY.iterdir()} == types


def test_the_shape_ignores_prose_but_not_fields() -> None:
    assert stored_shape(NoteV1Described) == stored_shape(NoteV1)
    assert stored_shape(NoteV1Changed) != stored_shape(NoteV1)


def notes(
    document_type: type[PersistentDocument],
    files: EvolutionFiles,
) -> DocumentEvolution:
    return DocumentEvolution(NOTES_COLLECTION, document_type, files)


def test_the_refresh_tool_records_versions_and_refuses_unbumped_changes(
    tmp_path: Path,
) -> None:
    files = EvolutionFiles(tmp_path / "golden", tmp_path / "schemas")
    golden_v1 = files.golden_path(NOTES_COLLECTION, 1)

    assert notes(NoteV1, files).snapshot_status() is SnapshotStatus.MISSING
    assert notes(NoteV1, files).refresh() == []
    assert notes(NoteV1, files).snapshot_problems() == []
    assert notes(NoteV1, files).golden_problems() == []
    recorded_v1: str = golden_v1.read_text(encoding="utf-8")

    # NoteV1Changed has its own snapshot file name: copy NoteV1's.
    files.snapshot_path(NoteV1Changed).write_text(
        files.snapshot_path(NoteV1).read_text(encoding="utf-8"), encoding="utf-8"
    )
    changed = notes(NoteV1Changed, files)
    assert changed.snapshot_status() is SnapshotStatus.CHANGED_WITHOUT_BUMP
    assert "without a schema_version bump" in changed.refresh()[0]
    assert golden_v1.read_text(encoding="utf-8") == recorded_v1

    files.snapshot_path(NoteV2).write_text(
        files.snapshot_path(NoteV1).read_text(encoding="utf-8"), encoding="utf-8"
    )
    bumped = notes(NoteV2, files)
    assert bumped.snapshot_status() is SnapshotStatus.BEHIND
    assert bumped.golden_problems() != []
    assert bumped.refresh() == []
    assert bumped.snapshot_problems() == bumped.golden_problems() == []
    assert files.golden_versions(NOTES_COLLECTION) == [1, 2]
    assert golden_v1.read_text(encoding="utf-8") == recorded_v1


def test_versions_never_go_down_and_gaps_are_reported(tmp_path: Path) -> None:
    files = EvolutionFiles(tmp_path / "golden", tmp_path / "schemas")
    assert notes(NoteV2, files).refresh() == []
    files.snapshot_path(NoteV1).write_text(
        files.snapshot_path(NoteV2).read_text(encoding="utf-8"), encoding="utf-8"
    )

    assert notes(NoteV1, files).snapshot_status() is SnapshotStatus.VERSION_WENT_DOWN
    assert notes(NoteV1, files).refresh() != []

    files.golden_path(NOTES_COLLECTION, 4).write_text("{}", encoding="utf-8")
    assert "without gaps" in notes(NoteV2, files).golden_problems()[0]


def test_a_renamed_type_leaves_a_stale_snapshot(tmp_path: Path) -> None:
    files = EvolutionFiles(tmp_path / "golden", tmp_path / "schemas")
    assert notes(NoteV1, files).refresh() == []
    stale = DocumentEvolution(DocumentCollectionName("other_notes"), NoteV1, files)

    assert stale.snapshot_status() is SnapshotStatus.STALE
    assert "stale" in stale.snapshot_problems()[0]
