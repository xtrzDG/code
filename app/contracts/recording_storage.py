"""Storage of call recordings (EU object storage in the concept)."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.typings.conversations.strings import RecordingStoragePath


class RecordingStorageAdapterContract(AdapterContract, Protocol):
    def delete(self, recording_path: RecordingStoragePath) -> None:
        """Delete a recording; deleting a missing recording is not an error."""
        raise NotImplementedError
