"""
Where customer files are kept: sealed with the business's key in the EU
bucket (AES-256-GCM, per-file keys, key rotation), or as plain files under
one directory in development, never outside it.
"""

from pathlib import Path

import pytest

from app.adapters.media.encrypted_object_media_storage_adapter import (
    EncryptedObjectMediaStorageAdapter,
)
from app.adapters.media.local_media_storage_adapter import LocalMediaStorageAdapter
from app.adapters.media.media_storage_factory import build_media_storage
from app.schemas.dto.media import MediaLocation, StoredMediaFile
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import MessageMediaId
from app.schemas.typings.media.strings import MediaStoragePath
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.media.media_paths import media_storage_path
from app.utilities.security.media_encryption import (
    HEADER_SIZE,
    open_media,
    read_media_header,
    seal_media,
)
from tests.channels.channels_settings import build_settings
from tests.media.media_fakes import jpeg_bytes, ogg_opus_bytes
from tests.security.previous_key_fakes import DictObjectStorage

MASTER: PlatformSecret = PlatformSecret("media-master-secret-0000")  # gitleaks:allow
OTHER_MASTER: PlatformSecret = PlatformSecret(
    "media-other-secret-0000"
)  # gitleaks:allow
BUSINESS: BusinessId = BusinessId()
OTHER_BUSINESS: BusinessId = BusinessId()


def location_of(
    business_id: BusinessId = BUSINESS, media_type: str = "audio/ogg"
) -> MediaLocation:
    return MediaLocation(
        business_id=business_id,
        path=media_storage_path(
            business_id,
            MessageMediaId(f"message_media_{'1' * 8}-1111-5111-8111-{'1' * 12}"),
            MessageMediaType(media_type),
        ),
    )


def voice_note() -> StoredMediaFile:
    return StoredMediaFile(
        content=ogg_opus_bytes(), media_type=MessageMediaType("audio/ogg")
    )


class TestEncryptedObjectStorage:
    def test_a_file_round_trips_and_the_bucket_only_sees_ciphertext(self) -> None:
        bucket = DictObjectStorage()
        storage = EncryptedObjectMediaStorageAdapter(bucket, MASTER)
        location = location_of()

        storage.store(location, voice_note())

        [(key, sealed)] = bucket.objects.items()
        assert key == str(location.path)
        assert key.startswith("message-media/")
        assert voice_note().content not in sealed
        assert storage.read(location) == voice_note()

    def test_each_file_gets_its_own_salt_and_nonce(self) -> None:
        bucket = DictObjectStorage()
        storage = EncryptedObjectMediaStorageAdapter(bucket, MASTER)
        first, second = location_of(), location_of(OTHER_BUSINESS)

        storage.store(first, voice_note())
        storage.store(second, voice_note())

        sealed_first = bucket.objects[str(first.path)]
        sealed_second = bucket.objects[str(second.path)]
        assert sealed_first[:HEADER_SIZE] != sealed_second[:HEADER_SIZE]
        assert sealed_first[HEADER_SIZE:] != sealed_second[HEADER_SIZE:]

    def test_another_business_path_or_key_does_not_open_a_file(self) -> None:
        location = location_of()
        sealed = seal_media(MASTER, location, voice_note(), b"s" * 16, b"n" * 12)

        moved = MediaLocation(business_id=OTHER_BUSINESS, path=location.path)
        with pytest.raises(ExternalServiceError, match="does not open"):
            open_media(MASTER, moved, sealed)
        with pytest.raises(ExternalServiceError, match="another ENCRYPTION_KEY"):
            open_media(OTHER_MASTER, location, sealed)

        tampered = sealed[:-1] + bytes([sealed[-1] ^ 1])
        with pytest.raises(ExternalServiceError, match="does not open"):
            open_media(MASTER, location, tampered)

    def test_a_file_of_the_previous_key_still_opens_after_rotation(self) -> None:
        bucket = DictObjectStorage()
        location = location_of()
        EncryptedObjectMediaStorageAdapter(bucket, OTHER_MASTER).store(
            location, voice_note()
        )

        rotated = EncryptedObjectMediaStorageAdapter(
            bucket, MASTER, previous_master_secrets=[OTHER_MASTER]
        )

        assert rotated.read(location) == voice_note()

    def test_something_that_is_not_a_sealed_file_is_refused(self) -> None:
        with pytest.raises(ExternalServiceError, match="not an encrypted"):
            read_media_header(b"plain bytes")

        location = location_of()
        sealed = bytearray(
            seal_media(MASTER, location, voice_note(), b"s" * 16, b"n" * 12)
        )
        type_at = 4 + 8 + 16 + 12
        sealed[type_at : type_at + 4] = "é".encode() + b"xy"
        with pytest.raises(ExternalServiceError, match="broken header"):
            read_media_header(bytes(sealed))

    def test_a_missing_file_reads_as_none_and_delete_removes_it(self) -> None:
        bucket = DictObjectStorage()
        storage = EncryptedObjectMediaStorageAdapter(bucket, MASTER)
        location = location_of()
        assert storage.read(location) is None

        storage.store(location, voice_note())
        storage.delete(location)
        storage.delete(location)

        assert bucket.objects == {}

    @pytest.mark.parametrize("path", ["", "/etc/passwd", "message-media/../x.ogg"])
    def test_paths_outside_the_media_keys_are_refused(self, path: str) -> None:
        storage = EncryptedObjectMediaStorageAdapter(DictObjectStorage(), MASTER)
        location = MediaLocation(business_id=BUSINESS, path=MediaStoragePath(path))
        with pytest.raises(ValidationFailedError):
            storage.store(location, voice_note())


class TestLocalStorage:
    def test_files_round_trip_with_the_type_of_their_extension(
        self, tmp_path: Path
    ) -> None:
        storage = LocalMediaStorageAdapter(tmp_path)
        photo = StoredMediaFile(
            content=jpeg_bytes(), media_type=MessageMediaType("image/jpeg")
        )
        location = location_of(media_type="image/jpeg")

        storage.store(location, photo)

        assert storage.read(location) == photo
        assert (tmp_path / str(location.path)).read_bytes() == jpeg_bytes()
        assert not any(path.name.endswith(".partial") for path in tmp_path.rglob("*"))
        storage.delete(location)
        assert storage.read(location) is None

    def test_unknown_extensions_and_missing_files_read_as_none(
        self, tmp_path: Path
    ) -> None:
        storage = LocalMediaStorageAdapter(tmp_path)
        (tmp_path / "message-media").mkdir()
        (tmp_path / "message-media" / "note.exe").write_bytes(b"MZ")

        unknown = MediaLocation(
            business_id=BUSINESS, path=MediaStoragePath("message-media/note.exe")
        )
        assert storage.read(unknown) is None
        assert storage.read(location_of()) is None

    @pytest.mark.parametrize(
        "path", ["", "../outside.ogg", "message-media/../../x.ogg", "a\x00b.ogg", "."]
    )
    def test_paths_never_leave_the_directory(self, tmp_path: Path, path: str) -> None:
        storage = LocalMediaStorageAdapter(tmp_path / "media")
        location = MediaLocation(business_id=BUSINESS, path=MediaStoragePath(path))
        with pytest.raises(ValidationFailedError):
            storage.store(location, voice_note())

    def test_a_directory_is_never_deleted(self, tmp_path: Path) -> None:
        storage = LocalMediaStorageAdapter(tmp_path)
        (tmp_path / "message-media").mkdir()
        location = MediaLocation(
            business_id=BUSINESS, path=MediaStoragePath("message-media")
        )
        with pytest.raises(ValidationFailedError):
            storage.delete(location)


def test_the_factory_keeps_files_where_recordings_are_kept(tmp_path: Path) -> None:
    settings = build_settings(RECORDINGS_DIRECTORY=str(tmp_path))

    local = build_media_storage(settings, None)
    encrypted = build_media_storage(settings, DictObjectStorage())

    assert isinstance(local, LocalMediaStorageAdapter)
    assert isinstance(encrypted, EncryptedObjectMediaStorageAdapter)
