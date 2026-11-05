"""Archives read back whole in tests (the app streams them a piece at a time)."""

from collections.abc import Iterable

from app.contracts.export_archives import ExportArchiveStorageContract
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.strings import ExportArchivePath


def read_whole(
    storage: ExportArchiveStorageContract,
    business_id: BusinessId,
    path: ExportArchivePath,
) -> bytes | None:
    pieces: Iterable[bytes] | None = storage.stream(business_id, path)
    return None if pieces is None else b"".join(pieces)
