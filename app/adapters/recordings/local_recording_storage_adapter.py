import logging
import os
from pathlib import Path

from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingLocation,
    RecordingPart,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.conversations.constrained_integers import (
    RecordingByteCount,
    RecordingByteOffset,
)
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.utilities.channels.voice_recordings import recording_media_type_of_file
from app.utilities.recordings.recording_byte_ranges import resolve_byte_span

logger: logging.Logger = logging.getLogger(__name__)


class LocalRecordingStorageAdapter(RecordingStorageAdapterContract):
    """
    Call recordings kept as files under one directory: development only
    (RECORDINGS_STORAGE=local). Several API instances do not share a disk,
    so production keeps recordings in EU object storage
    (`EncryptedObjectRecordingStorageAdapter`) behind the same contract.

    Recording paths are relative to the root and may not leave it; the
    media type of a recording comes from its file extension. A byte range
    is read with a seek, not by loading the whole file.
    """

    def __init__(self, root_directory: Path) -> None:
        self._root_directory: Path = root_directory.resolve()

    def read(
        self,
        location: RecordingLocation,
        wanted: RecordingByteRange | None = None,
    ) -> RecordingPart | None:
        try:
            file_path: Path = self.resolve_path(location.path)
        except ValidationFailedError:
            # A stored path that leaves the directory names no recording here.
            logger.warning("Recording path %r is not readable here.", location.path)
            return None

        try:
            with file_path.open("rb") as recording:
                total: int = os.fstat(recording.fileno()).st_size
                span: tuple[int, int] | None = (
                    (0, total - 1)
                    if wanted is None
                    else resolve_byte_span(wanted, total)
                )
                first_byte: int = total if span is None else span[0]
                content: bytes = b""
                if span is not None and total > 0:
                    recording.seek(span[0])
                    content = recording.read(span[1] - span[0] + 1)
        except FileNotFoundError, IsADirectoryError, NotADirectoryError:
            return None

        return RecordingPart(
            content=content,
            media_type=recording_media_type_of_file(file_path.name),
            first_byte=RecordingByteOffset(first_byte if total > 0 else 0),
            total_bytes=RecordingByteCount(total),
        )

    def store(self, location: RecordingLocation, audio: RecordingAudio) -> None:
        file_path: Path = self.resolve_path(location.path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Written beside it and renamed: a reader never sees half a file.
        partial_path: Path = file_path.with_name(f".{file_path.name}.partial")
        partial_path.write_bytes(audio.content)
        partial_path.replace(file_path)

    def delete(self, location: RecordingLocation) -> None:
        file_path: Path = self.resolve_path(location.path)
        if file_path.is_dir():
            raise ValidationFailedError(
                f"Recording path {location.path!r} is a directory, not a recording."
            )

        file_path.unlink(missing_ok=True)

    def resolve_path(self, recording_path: RecordingStoragePath) -> Path:
        """Return the file of a recording; refuse paths outside the root."""

        relative_path: str = recording_path.lstrip("/")
        if relative_path == "" or "\x00" in relative_path:
            raise ValidationFailedError(f"Invalid recording path {recording_path!r}.")

        file_path: Path = (self._root_directory / relative_path).resolve()
        if not file_path.is_relative_to(self._root_directory):
            raise ValidationFailedError(
                f"Recording path {recording_path!r} leaves the recordings directory."
            )

        if file_path == self._root_directory:
            raise ValidationFailedError(f"Invalid recording path {recording_path!r}.")

        return file_path
