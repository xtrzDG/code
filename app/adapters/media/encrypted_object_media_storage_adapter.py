import os
from collections.abc import Callable, Sequence

from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.object_storage import ObjectStorageClientContract
from app.schemas.dto.media import MediaLocation, StoredMediaFile
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.security.media_encryption import (
    NONCE_SIZE,
    SALT_SIZE,
    open_media,
    read_media_header,
    seal_media,
)
from app.utilities.security.recording_encryption import master_key_id

# Larger than any file the platform downloads: a read asks for the whole
# object (the client returns fewer bytes at its end).
WHOLE_OBJECT_LAST_BYTE: int = 2**40


class EncryptedObjectMediaStorageAdapter(MediaStorageAdapterContract):
    """
    Customer files in the recordings' S3-compatible EU bucket (keys under
    `message-media/`), each sealed with its business's key
    (`media_encryption`), so the bucket only ever sees ciphertext. New files
    are sealed under the current key of the ring; a file's header names the
    key it was sealed under, so files of a previous key (ENCRYPTION_KEYS)
    still open while that key is in the ring.
    """

    def __init__(
        self,
        client: ObjectStorageClientContract,
        master_secret: PlatformSecret,
        random_bytes: Callable[[int], bytes] = os.urandom,
        previous_master_secrets: Sequence[PlatformSecret] = (),
    ) -> None:
        self._client: ObjectStorageClientContract = client
        self._master_secret: PlatformSecret = master_secret
        self._secrets_by_key_id: dict[bytes, PlatformSecret] = {
            master_key_id(secret): secret
            for secret in reversed([master_secret, *previous_master_secrets])
        }
        self._random_bytes: Callable[[int], bytes] = random_bytes

    def store(self, location: MediaLocation, media: StoredMediaFile) -> None:
        self._client.put_object(
            object_key(location),
            seal_media(
                self._master_secret,
                location,
                media,
                self._random_bytes(SALT_SIZE),
                self._random_bytes(NONCE_SIZE),
            ),
        )

    def read(self, location: MediaLocation) -> StoredMediaFile | None:
        sealed: bytes | None = self._client.get_object_range(
            object_key(location), 0, WHOLE_OBJECT_LAST_BYTE
        )
        if sealed is None:
            return None

        key_id: bytes = read_media_header(sealed).key_id
        return open_media(
            self._secrets_by_key_id.get(key_id, self._master_secret), location, sealed
        )

    def delete(self, location: MediaLocation) -> None:
        self._client.delete_object(object_key(location))


def object_key(location: MediaLocation) -> RecordingStoragePath:
    """
    The bucket key of a file (the bucket is the recordings' one, so its keys
    are recording storage paths); refuses an empty, absolute or `..` path.
    """

    path: str = str(location.path)
    if path == "" or path.startswith("/") or "\x00" in path or ".." in path.split("/"):
        raise ValidationFailedError(f"Invalid media path {path!r}.")

    return RecordingStoragePath(path)
