from pathlib import Path

from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.conversations.strings import RecordingStoragePath


class LocalRecordingStorageAdapter(RecordingStorageAdapterContract):
    """
    Call recordings kept as files under one directory.

    For development and single-server installs; production keeps recordings
    in EU object storage behind the same contract. Recording paths are
    relative to the root and may not leave it.
    """

    def __init__(self, root_directory: Path) -> None:
        self._root_directory: Path = root_directory.resolve()

    def delete(self, recording_path: RecordingStoragePath) -> None:
        file_path: Path = self.resolve_path(recording_path)
        if file_path.is_dir():
            raise ValidationFailedError(
                f"Recording path {recording_path!r} is a directory, not a recording."
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
