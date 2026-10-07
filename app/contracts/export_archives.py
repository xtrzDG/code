"""Storage of the archives of full business exports, encrypted at rest."""

from collections.abc import Iterable
from typing import BinaryIO, Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.strings import ExportArchivePath


class ExportArchiveStorageContract(AdapterContract, Protocol):
    def store(
        self, business_id: BusinessId, path: ExportArchivePath, archive: BinaryIO
    ) -> None:
        """
        Keep a business's archive at its path (replacing one stored there),
        read from the start of `archive` (a file) to its end a piece at a
        time, so an archive of any size never sits in memory whole.
        Raises ValidationFailedError for a path this storage does not keep,
        ExternalServiceError when the storage cannot be reached.
        """
        raise NotImplementedError

    def stream(
        self, business_id: BusinessId, path: ExportArchivePath
    ) -> Iterable[bytes] | None:
        """
        The archive's bytes in pieces of about a megabyte, read and opened
        a piece at a time as they are consumed, so a download never holds
        the archive whole; None when it is gone (expired and purged). The
        storage is reached and the archive's key checked before this
        returns. Raises ExternalServiceError when it does not open; a piece
        found changed or cut off later raises it from the iteration.
        """
        raise NotImplementedError

    def delete(self, business_id: BusinessId, path: ExportArchivePath) -> None:
        """Delete an archive; deleting a missing one is not an error."""
        raise NotImplementedError
