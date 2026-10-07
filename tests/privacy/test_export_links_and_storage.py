"""
The one-time download tokens of full exports and the storage of their
archives: a token is random and stored only as its hash; an archive is
sealed with its business's key and opens only there.
"""

import io
from pathlib import Path

import pytest

from app.adapters.exports.encrypted_object_export_archive_storage_adapter import (
    EncryptedObjectExportArchiveStorageAdapter,
)
from app.adapters.exports.export_archive_storage_factory import (
    build_export_archive_storage,
)
from app.adapters.exports.local_export_archive_storage_adapter import (
    LocalExportArchiveStorageAdapter,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.constrained_strings import BusinessExportToken
from app.schemas.typings.privacy.prefixed_id import BusinessExportId
from app.schemas.typings.privacy.strings import ExportArchivePath
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.privacy.export_download_tokens import (
    download_link_id,
    generate_download_token,
    hash_download_token,
    is_same_hash,
)
from tests.exports.archive_reading import read_whole
from tests.security.previous_key_fakes import DictObjectStorage

BUSINESS: BusinessId = BusinessId()
OTHER_BUSINESS: BusinessId = BusinessId()
EXPORT: BusinessExportId = BusinessExportId()
PATH: ExportArchivePath = ExportArchivePath(f"business-exports/{BUSINESS}/{EXPORT}.zip")
NEW_KEY: PlatformSecret = PlatformSecret("new-export-key-0000")


def test_a_token_is_random_and_kept_only_as_its_hash() -> None:
    token = generate_download_token()
    other = generate_download_token()
    token_hash = hash_download_token(token)

    assert token != other
    assert len(str(token)) == 43
    assert str(token) not in str(token_hash)
    assert download_link_id(token_hash) == download_link_id(
        hash_download_token(BusinessExportToken(str(token)))
    )
    assert download_link_id(token_hash) != download_link_id(hash_download_token(other))
    assert is_same_hash(token_hash, hash_download_token(token))
    assert not is_same_hash(token_hash, hash_download_token(other))


def test_an_archive_is_sealed_with_its_business_key() -> None:
    objects = DictObjectStorage()
    storage = EncryptedObjectExportArchiveStorageAdapter(objects, NEW_KEY)

    storage.store(BUSINESS, PATH, io.BytesIO(b"PK zip bytes of Giorgi"))

    [sealed] = objects.objects.values()
    assert b"Giorgi" not in sealed
    assert read_whole(storage, BUSINESS, PATH) == b"PK zip bytes of Giorgi"
    with pytest.raises(ExternalServiceError):
        read_whole(storage, OTHER_BUSINESS, PATH)
    rotated = EncryptedObjectExportArchiveStorageAdapter(
        objects, PlatformSecret("newest-key-0000"), previous_master_secrets=[NEW_KEY]
    )
    assert read_whole(rotated, BUSINESS, PATH) == b"PK zip bytes of Giorgi"
    storage.delete(BUSINESS, PATH)
    assert read_whole(storage, BUSINESS, PATH) is None
    with pytest.raises(ValidationFailedError):
        storage.store(BUSINESS, ExportArchivePath("../escape.zip"), io.BytesIO(b"x"))


def test_development_keeps_archives_as_files_inside_one_directory(
    tmp_path: Path,
) -> None:
    storage = LocalExportArchiveStorageAdapter(tmp_path)

    storage.store(BUSINESS, PATH, io.BytesIO(b"zip"))

    assert (tmp_path / str(PATH)).read_bytes() == b"zip"
    assert read_whole(storage, BUSINESS, PATH) == b"zip"
    storage.delete(BUSINESS, PATH)
    assert read_whole(storage, BUSINESS, PATH) is None
    with pytest.raises(ValidationFailedError):
        read_whole(storage, BUSINESS, ExportArchivePath("../../etc/passwd"))


def test_the_storage_follows_the_recordings_storage(tmp_path: Path) -> None:
    settings = assemble_app_settings({"RECORDINGS_DIRECTORY": str(tmp_path)})

    local = build_export_archive_storage(settings, None)
    remote = build_export_archive_storage(
        settings.model_copy(update={"encryption_key": NEW_KEY}), DictObjectStorage()
    )

    assert isinstance(local, LocalExportArchiveStorageAdapter)
    assert isinstance(remote, EncryptedObjectExportArchiveStorageAdapter)
