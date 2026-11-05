import shutil
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import BinaryIO

from app.contracts.export_archives import ExportArchiveStorageContract
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.strings import ExportArchivePath

# Copied a megabyte at a time.
COPY_BLOCK_SIZE: int = 1024 * 1024


class LocalExportArchiveStorageAdapter(ExportArchiveStorageContract):
    """
    Export archives kept as files under one directory: development only
    (RECORDINGS_STORAGE=local, under RECORDINGS_DIRECTORY). Production keeps
    them encrypted in the EU bucket
    (`EncryptedObjectExportArchiveStorageAdapter`) behind the same contract.
    Paths stay inside the directory.
    """

    def __init__(self, root_directory: Path) -> None:
        self._root_directory: Path = root_directory.resolve()

    def store(
        self, business_id: BusinessId, path: ExportArchivePath, archive: BinaryIO
    ) -> None:
        file_path: Path = self.resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Written beside it and renamed: a reader never sees half a file.
        partial_path: Path = file_path.with_name(f".{file_path.name}.partial")
        archive.seek(0)
        with partial_path.open("wb") as partial:
            shutil.copyfileobj(archive, partial, COPY_BLOCK_SIZE)
        partial_path.replace(file_path)

    def stream(
        self, business_id: BusinessId, path: ExportArchivePath
    ) -> Iterable[bytes] | None:
        try:
            archive: BinaryIO = self.resolve_path(path).open("rb")
        except FileNotFoundError, IsADirectoryError, NotADirectoryError:
            return None

        return read_pieces(archive)

    def delete(self, business_id: BusinessId, path: ExportArchivePath) -> None:
        self.resolve_path(path).unlink(missing_ok=True)

    def resolve_path(self, path: ExportArchivePath) -> Path:
        """The file of an archive; refuses paths outside the directory."""

        relative_path: str = str(path).lstrip("/")
        if relative_path == "" or "\x00" in relative_path:
            raise ValidationFailedError(f"Invalid export path {path!r}.")

        file_path: Path = (self._root_directory / relative_path).resolve()
        if (
            not file_path.is_relative_to(self._root_directory)
            or file_path == self._root_directory
        ):
            raise ValidationFailedError(f"Invalid export path {path!r}.")

        return file_path


def read_pieces(archive: BinaryIO) -> Iterator[bytes]:
    """The file a megabyte at a time, closed once read to its end."""

    with archive:
        while piece := archive.read(COPY_BLOCK_SIZE):
            yield piece
