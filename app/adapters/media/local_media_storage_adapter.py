from pathlib import Path

from app.contracts.media_storage import MediaStorageAdapterContract
from app.schemas.dto.media import MediaLocation, StoredMediaFile
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.utilities.media.media_paths import media_type_of_extension


class LocalMediaStorageAdapter(MediaStorageAdapterContract):
    """
    Customer files kept as files under one directory: development only
    (RECORDINGS_STORAGE=local, under RECORDINGS_DIRECTORY). Production keeps
    them encrypted in the EU bucket (`EncryptedObjectMediaStorageAdapter`)
    behind the same contract. Paths stay inside the directory; a file's
    media type comes from its extension.
    """

    def __init__(self, root_directory: Path) -> None:
        self._root_directory: Path = root_directory.resolve()

    def store(self, location: MediaLocation, media: StoredMediaFile) -> None:
        file_path: Path = self.resolve_path(location)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Written beside it and renamed: a reader never sees half a file.
        partial_path: Path = file_path.with_name(f".{file_path.name}.partial")
        partial_path.write_bytes(media.content)
        partial_path.replace(file_path)

    def read(self, location: MediaLocation) -> StoredMediaFile | None:
        file_path: Path = self.resolve_path(location)
        media_type: MessageMediaType | None = media_type_of_extension(file_path.name)
        if media_type is None:
            return None

        try:
            content: bytes = file_path.read_bytes()
        except FileNotFoundError, IsADirectoryError, NotADirectoryError:
            return None

        return StoredMediaFile(content=content, media_type=media_type)

    def delete(self, location: MediaLocation) -> None:
        file_path: Path = self.resolve_path(location)
        if file_path.is_dir():
            raise ValidationFailedError(f"Media path {location.path!r} is a directory.")

        file_path.unlink(missing_ok=True)

    def resolve_path(self, location: MediaLocation) -> Path:
        """The file of a location; refuses paths outside the directory."""

        relative_path: str = str(location.path).lstrip("/")
        if relative_path == "" or "\x00" in relative_path:
            raise ValidationFailedError(f"Invalid media path {location.path!r}.")

        file_path: Path = (self._root_directory / relative_path).resolve()
        if (
            not file_path.is_relative_to(self._root_directory)
            or file_path == self._root_directory
        ):
            raise ValidationFailedError(
                f"Media path {location.path!r} leaves the media directory."
            )

        return file_path
