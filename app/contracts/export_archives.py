"""Storage of the archives of full business exports, encrypted at rest."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.strings import ExportArchivePath


class ExportArchiveStorageContract(AdapterContract, Protocol):
    def store(
        self, business_id: BusinessId, path: ExportArchivePath, archive: bytes
    ) -> None:
        """
        Keep a business's archive at its path (replacing one stored there).
        Raises ValidationFailedError for a path this storage does not keep,
        ExternalServiceError when the storage cannot be reached.
        """
        raise NotImplementedError

    def read(self, business_id: BusinessId, path: ExportArchivePath) -> bytes | None:
        """
        The archive's bytes; None when it is gone (expired and purged).
        Raises ExternalServiceError when it does not open.
        """
        raise NotImplementedError

    def delete(self, business_id: BusinessId, path: ExportArchivePath) -> None:
        """Delete an archive; deleting a missing one is not an error."""
        raise NotImplementedError
