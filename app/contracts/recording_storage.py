"""Storage of call recordings (EU object storage in the concept)."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingLocation,
    RecordingPart,
)


class RecordingStorageAdapterContract(AdapterContract, Protocol):
    def read(
        self,
        location: RecordingLocation,
        wanted: RecordingByteRange | None = None,
    ) -> RecordingPart | None:
        """
        The whole recording, or the part a media player asked for, with its
        media type and total length; an empty part when the range lies
        outside the recording. None when it is gone (deleted, purged, never
        stored). Raises ExternalServiceError when the storage cannot be
        reached or the recording does not open.
        """
        raise NotImplementedError

    def store(self, location: RecordingLocation, audio: RecordingAudio) -> None:
        """
        Keep a recording at its location (replacing one stored there).
        Raises ValidationFailedError for a location this storage does not
        keep, ExternalServiceError when the storage cannot be reached.
        """
        raise NotImplementedError

    def delete(self, location: RecordingLocation) -> None:
        """Delete a recording; deleting a missing recording is not an error."""
        raise NotImplementedError
