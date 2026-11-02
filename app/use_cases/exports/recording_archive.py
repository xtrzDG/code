"""
The calls' recordings in a full export (Data Act art. 26; GDPR art. 20):
each recording the business still keeps is copied under recordings/ as
its audio file (named by the call's id), read from the recording storage
a megabyte at a time, so the worker never holds a recording whole. The
archive's recordings stop at MAX_ARCHIVED_RECORDING_BYTES: a recording
past that is listed with the API path that downloads it instead.
recordings.json lists every call with a recording and what the archive
holds of it (`ArchivedRecording`). A recording the storage no longer has,
or cannot give, is listed as such and never fails the export.
"""

import json
import logging
import zipfile
from dataclasses import dataclass

from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories.conversation_repositories import CallRepoContract
from app.schemas.constants.privacy import ArchivedRecordingStatus
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.call_recordings import (
    RecordingByteRange,
    RecordingLocation,
    RecordingPart,
)
from app.schemas.dto.privacy.archived_recordings import ArchivedRecording
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_integers import (
    RecordingByteCount,
    RecordingByteOffset,
)
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.privacy.constrained_strings import (
    ArchivedRecordingFile,
    CallRecordingDownloadPath,
)
from app.use_cases.shared.document_pages import pages_in_write_order

LOGGER: logging.Logger = logging.getLogger(__name__)
MANIFEST_NAME: str = "recordings.json"
CHUNK_BYTES: int = 1024 * 1024
# The archive's audio at most (2 GiB); the rest is listed by download path.
MAX_ARCHIVED_RECORDING_BYTES: int = 2 * 1024 * 1024 * 1024
EXTENSIONS: dict[str, str] = {
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/ogg": "ogg",
    "audio/webm": "webm",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
}


@dataclass(frozen=True)
class RecordingArchive:
    call_repo: CallRepoContract
    recording_storage: RecordingStorageAdapterContract
    max_bytes: int = MAX_ARCHIVED_RECORDING_BYTES

    def write(self, archive: zipfile.ZipFile, business_id: BusinessId) -> int:
        """Copy the recordings and write their list; how many it lists."""

        listed: list[ArchivedRecording] = []
        room: int = self.max_bytes
        for page in pages_in_write_order(
            self.call_repo, business_id, lambda call: str(call.id)
        ):
            for call in page:
                if call.recording_path is None or call.recording_declined:
                    continue

                entry, written = self._copy(archive, call, call.recording_path, room)
                room -= written
                listed.append(entry)

        archive.writestr(
            MANIFEST_NAME,
            json.dumps([entry.model_dump(mode="json") for entry in listed], indent=1),
        )
        return len(listed)

    def _copy(
        self,
        archive: zipfile.ZipFile,
        call: CallDocument,
        path: RecordingStoragePath,
        room: int,
    ) -> tuple[ArchivedRecording, int]:
        """The call's entry in the list, and how many bytes it added."""

        location = RecordingLocation(business_id=call.business_id, path=path)
        listed = ArchivedRecording(
            call_id=call.id,
            conversation_id=call.conversation_id,
            started_at=call.started_at,
            status=ArchivedRecordingStatus.UNAVAILABLE,
            download_path=CallRecordingDownloadPath(
                f"/v1/businesses/{call.business_id}/calls/{call.id}/recording"
            ),
        )
        first: RecordingPart | None = self._read(location, 0)
        if first is None:
            return listed, 0

        total: int = int(first.total_bytes)
        described = listed.model_copy(
            update={
                "media_type": first.media_type,
                "total_bytes": RecordingByteCount(total),
            }
        )
        if total > room:
            return described.model_copy(
                update={"status": ArchivedRecordingStatus.LEFT_OUT}
            ), 0

        file = ArchivedRecordingFile(
            f"recordings/{call.id}.{EXTENSIONS.get(str(first.media_type), 'bin')}"
        )
        written: int = 0
        part: RecordingPart | None = first
        with archive.open(str(file), "w", force_zip64=True) as stream:
            while part is not None and part.content:
                stream.write(part.content)
                written += len(part.content)
                part = self._read(location, written) if written < total else None

        status = (
            ArchivedRecordingStatus.INCLUDED
            if written >= total
            else ArchivedRecordingStatus.INCOMPLETE
        )
        return described.model_copy(update={"status": status, "file": file}), written

    def _read(self, location: RecordingLocation, offset: int) -> RecordingPart | None:
        """One megabyte from `offset`; None when the storage cannot give it."""

        try:
            return self.recording_storage.read(
                location,
                RecordingByteRange(
                    first_byte=RecordingByteOffset(offset),
                    last_byte=RecordingByteOffset(offset + CHUNK_BYTES - 1),
                ),
            )
        except ExternalServiceError as error:
            LOGGER.warning(
                "A recording of %s could not be read for an export: %s",
                location.business_id,
                type(error).__name__,
            )
            return None
