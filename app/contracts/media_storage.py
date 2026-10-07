"""Storage of the files customers send (voice notes, photos), encrypted."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.media import MediaLocation, StoredMediaFile


class MediaStorageAdapterContract(AdapterContract, Protocol):
    def store(self, location: MediaLocation, media: StoredMediaFile) -> None:
        """
        Keep a file at its location (replacing one stored there). Raises
        ValidationFailedError for a location this storage does not keep,
        ExternalServiceError when the storage cannot be reached.
        """
        raise NotImplementedError

    def read(self, location: MediaLocation) -> StoredMediaFile | None:
        """
        The file; None when it is gone (purged, erased, never stored).
        Raises ExternalServiceError when the storage cannot be reached or
        the file does not open.
        """
        raise NotImplementedError

    def delete(self, location: MediaLocation) -> None:
        """Delete a file; deleting a missing file is not an error."""
        raise NotImplementedError
