"""Storage of call recordings (EU object storage in the concept)."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.call_recordings import RecordingAudio
from app.schemas.typings.conversations.strings import RecordingStoragePath


class RecordingStorageAdapterContract(AdapterContract, Protocol):
    def read(self, recording_path: RecordingStoragePath) -> RecordingAudio | None:
        """
        The audio of a recording with its media type; None when it is gone
        (deleted, purged, never stored). Raises ExternalServiceError when
        the storage cannot be reached.
        """
        raise NotImplementedError

    def delete(self, recording_path: RecordingStoragePath) -> None:
        """Delete a recording; deleting a missing recording is not an error."""
        raise NotImplementedError
