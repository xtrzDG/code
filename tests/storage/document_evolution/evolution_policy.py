"""
The rules that tie a stored document type's shape to its schema version,
shared by the policy test and the refresh tool:

1. the snapshot records the current shape at the current version: a shape
   change needs a `schema_version` bump;
2. the current version has a golden fixture, and the kept fixtures run
   without gaps from the oldest one up to the current version.
"""

from dataclasses import dataclass
from enum import StrEnum

from base_pydantic_schemas import PersistentDocument

from app.adapters.storage.document_upgrades import declared_schema_version
from app.adapters.storage.persisted_document_codec import (
    PersistedDocumentCodec,
    parse_stored_object,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from tests.storage.document_evolution.evolution_files import (
    EvolutionFiles,
    JsonValue,
    build_snapshot,
    stored_shape,
    write_json,
)
from tests.storage.document_evolution.sample_documents import sample_document

REFRESH_COMMAND: str = "uv run python -m tests.storage.document_evolution.refresh"


class SnapshotStatus(StrEnum):
    UP_TO_DATE = "up_to_date"
    MISSING = "missing"
    CHANGED_WITHOUT_BUMP = "changed_without_bump"
    VERSION_WENT_DOWN = "version_went_down"
    BEHIND = "behind"
    STALE = "stale"


# The refresh tool records everything else, but never these.
REFUSED_STATUSES: frozenset[SnapshotStatus] = frozenset(
    {SnapshotStatus.CHANGED_WITHOUT_BUMP, SnapshotStatus.VERSION_WENT_DOWN}
)


@dataclass(frozen=True)
class DocumentEvolution:
    """A stored document type, its version, shape and recorded files."""

    collection_name: DocumentCollectionName
    document_type: type[PersistentDocument]
    files: EvolutionFiles

    @property
    def current_version(self) -> int:
        declared = declared_schema_version(self.document_type)
        assert declared is not None, f"{self.label} has no schema_version"
        return int(declared)

    @property
    def label(self) -> str:
        return f"{self.document_type.__name__} ({self.collection_name!s})"

    def shape(self) -> JsonValue:
        return stored_shape(self.document_type)

    def snapshot_status(self) -> SnapshotStatus:
        snapshot = self.files.read_snapshot(self.document_type)
        if snapshot is None:
            return SnapshotStatus.MISSING

        recorded_version: object = snapshot.get("schema_version")
        current: int = self.current_version
        if recorded_version == current and snapshot.get("shape") != self.shape():
            return SnapshotStatus.CHANGED_WITHOUT_BUMP

        if not isinstance(recorded_version, int) or recorded_version > current:
            return SnapshotStatus.VERSION_WENT_DOWN

        if recorded_version < current:
            return SnapshotStatus.BEHIND

        expected = build_snapshot(self.document_type, self.collection_name, current)
        return (
            SnapshotStatus.UP_TO_DATE if snapshot == expected else SnapshotStatus.STALE
        )

    def snapshot_problems(self) -> list[str]:
        status: SnapshotStatus = self.snapshot_status()
        current: int = self.current_version
        name: str = self.document_type.__name__
        messages: dict[SnapshotStatus, str] = {
            SnapshotStatus.MISSING: f"{self.label} has no schema snapshot",
            SnapshotStatus.CHANGED_WITHOUT_BUMP: (
                f"The stored shape of {self.label} changed without a "
                f"schema_version bump. Set `schema_version: SchemaVersion = "
                f'SchemaVersion("{current + 1}")` on {name}, register an upcaster '
                "in app/adapters/storage/document_upgrades.py if rows of the old "
                "shape need one (a renamed, removed or newly required field), "
                "and follow docs/operations/deploys.md"
            ),
            SnapshotStatus.VERSION_WENT_DOWN: (
                f"{self.label} is at version {current}, below its snapshot: "
                "versions only go up"
            ),
            SnapshotStatus.BEHIND: (
                f"{self.label} is at version {current}, its snapshot is older"
            ),
            SnapshotStatus.STALE: f"The snapshot of {self.label} is stale",
        }
        if status is SnapshotStatus.UP_TO_DATE:
            return []

        return [f"{messages[status]}; then run `{REFRESH_COMMAND}`."]

    def golden_problems(self) -> list[str]:
        versions: list[int] = self.files.golden_versions(self.collection_name)
        current: int = self.current_version
        if current not in versions:
            return [
                f"{self.label} has no golden fixture of version {current} "
                f"(tests/storage/golden/{self.collection_name!s}/v{current}.json); "
                f"run `{REFRESH_COMMAND}`."
            ]

        expected: list[int] = list(range(versions[0], current + 1))
        if versions != expected:
            return [
                f"Golden fixtures of {self.label} must run without gaps from the "
                f"oldest kept version to {current}: found {versions}."
            ]

        return []

    def refresh(self) -> list[str]:
        """
        Record the current version: write its golden fixture if missing
        (never overwriting one) and the snapshot. Refuses, returning the
        problem, a shape change without a version bump.
        """

        if self.snapshot_status() in REFUSED_STATUSES:
            return self.snapshot_problems()

        current: int = self.current_version
        golden = self.files.golden_path(self.collection_name, current)
        if not golden.exists():
            sample = sample_document(self.document_type, self.collection_name)
            codec = PersistedDocumentCodec(self.document_type, self.collection_name)
            write_json(golden, parse_stored_object(codec.encode(sample)))

        write_json(
            self.files.snapshot_path(self.document_type),
            build_snapshot(self.document_type, self.collection_name, current),
        )
        return []
