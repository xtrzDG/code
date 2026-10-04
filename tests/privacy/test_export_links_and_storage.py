"""
The signed download links of full exports and the storage of their
archives: a token names one export of one business and its expiry; an
archive is sealed with its business's key and opens only there.
"""

from pathlib import Path

import pytest
from typed_time_provider import Microseconds

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
from app.utilities.privacy.export_link_signer import BusinessExportLinkSigner
from tests.security.previous_key_fakes import DictObjectStorage

BUSINESS: BusinessId = BusinessId()
OTHER_BUSINESS: BusinessId = BusinessId()
EXPORT: BusinessExportId = BusinessExportId()
EXPIRES_AT: Microseconds = Microseconds(1_900_000_000_000_000)
PATH: ExportArchivePath = ExportArchivePath(f"business-exports/{BUSINESS}/{EXPORT}.zip")
OLD_KEY: PlatformSecret = PlatformSecret("old-export-key-0000")
NEW_KEY: PlatformSecret = PlatformSecret("new-export-key-0000")


def test_a_token_names_its_export_business_and_expiry() -> None:
    signer = BusinessExportLinkSigner(NEW_KEY)
    token = signer.sign(BUSINESS, EXPORT, EXPIRES_AT)

    assert signer.expiry_of(BUSINESS, EXPORT, token) == EXPIRES_AT
    assert signer.expiry_of(OTHER_BUSINESS, EXPORT, token) is None
    assert signer.expiry_of(BUSINESS, BusinessExportId(), token) is None
    assert signer.expiry_of(BUSINESS, EXPORT, BusinessExportToken("A" * 40)) is None
    assert BusinessExportLinkSigner(OLD_KEY).expiry_of(BUSINESS, EXPORT, token) is None


def test_a_link_of_the_previous_key_still_opens_after_a_rotation() -> None:
    token = BusinessExportLinkSigner(OLD_KEY).sign(BUSINESS, EXPORT, EXPIRES_AT)

    rotated = BusinessExportLinkSigner(NEW_KEY, previous_keys=[OLD_KEY])

    assert rotated.expiry_of(BUSINESS, EXPORT, token) == EXPIRES_AT


def test_an_archive_is_sealed_with_its_business_key() -> None:
    objects = DictObjectStorage()
    storage = EncryptedObjectExportArchiveStorageAdapter(objects, NEW_KEY)

    storage.store(BUSINESS, PATH, b"PK zip bytes of Giorgi")

    [sealed] = objects.objects.values()
    assert b"Giorgi" not in sealed
    assert storage.read(BUSINESS, PATH) == b"PK zip bytes of Giorgi"
    with pytest.raises(ExternalServiceError):
        storage.read(OTHER_BUSINESS, PATH)
    rotated = EncryptedObjectExportArchiveStorageAdapter(
        objects, PlatformSecret("newest-key-0000"), previous_master_secrets=[NEW_KEY]
    )
    assert rotated.read(BUSINESS, PATH) == b"PK zip bytes of Giorgi"
    storage.delete(BUSINESS, PATH)
    assert storage.read(BUSINESS, PATH) is None
    with pytest.raises(ValidationFailedError):
        storage.store(BUSINESS, ExportArchivePath("../escape.zip"), b"x")


def test_development_keeps_archives_as_files_inside_one_directory(
    tmp_path: Path,
) -> None:
    storage = LocalExportArchiveStorageAdapter(tmp_path)

    storage.store(BUSINESS, PATH, b"zip")

    assert (tmp_path / str(PATH)).read_bytes() == b"zip"
    assert storage.read(BUSINESS, PATH) == b"zip"
    storage.delete(BUSINESS, PATH)
    assert storage.read(BUSINESS, PATH) is None
    with pytest.raises(ValidationFailedError):
        storage.read(BUSINESS, ExportArchivePath("../../etc/passwd"))


def test_the_storage_follows_the_recordings_storage(tmp_path: Path) -> None:
    settings = assemble_app_settings({"RECORDINGS_DIRECTORY": str(tmp_path)})

    local = build_export_archive_storage(settings, None)
    remote = build_export_archive_storage(
        settings.model_copy(update={"encryption_key": NEW_KEY}), DictObjectStorage()
    )

    assert isinstance(local, LocalExportArchiveStorageAdapter)
    assert isinstance(remote, EncryptedObjectExportArchiveStorageAdapter)
