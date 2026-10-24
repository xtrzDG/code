from collections.abc import Callable

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.key_rotations import KeyRotationRepoContract
from app.schemas.constants.security import KeyRotationStatus
from app.schemas.domain.key_rotations import KeyRotationDocument
from app.schemas.typings.security.prefixed_id import KeyRotationId

# One document: the latest run (earlier ones live on in the audit log).
LATEST_ROTATION_KEY: str = "latest"
ACTIVE_STATUSES: frozenset[KeyRotationStatus] = frozenset(
    {KeyRotationStatus.QUEUED, KeyRotationStatus.RUNNING}
)


class KeyRotationRepository(KeyRotationRepoContract):
    """The latest re-encryption run, under one fixed key (platform-wide)."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[KeyRotationDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[KeyRotationDocument] = (
            collection
        )

    def get_latest(self) -> KeyRotationDocument | None:
        return self._collection.get(LATEST_ROTATION_KEY)

    def start(
        self,
        rotation: KeyRotationDocument,
        stale_before: Microseconds,
    ) -> bool:
        if self._collection.insert_if_absent(LATEST_ROTATION_KEY, rotation):
            return True

        def replace_finished(
            stored: KeyRotationDocument,
        ) -> KeyRotationDocument | None:
            is_active: bool = stored.status in ACTIVE_STATUSES and int(
                stored.updated_at
            ) >= int(stale_before)
            return None if is_active else rotation

        return (
            self._collection.modify(LATEST_ROTATION_KEY, replace_finished) is not None
        )

    def update(
        self,
        rotation_id: KeyRotationId,
        change: Callable[[KeyRotationDocument], KeyRotationDocument],
    ) -> KeyRotationDocument | None:
        def change_this_run(stored: KeyRotationDocument) -> KeyRotationDocument | None:
            return change(stored) if stored.id == rotation_id else None

        return self._collection.modify(LATEST_ROTATION_KEY, change_this_run)
