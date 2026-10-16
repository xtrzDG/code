"""
Off-site database backups: the bucket, the archive cipher, the dump and
the scratch database of the restore drill (docs/operations/backup-restore.md).
"""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.contracts.client_contract import ClientContract
from app.schemas.dto.backups import (
    BackupObjectListing,
    DatabaseFacts,
    RestoredDatabase,
)
from app.schemas.typings.backups.booleans import IsScratchDatabaseKept
from app.schemas.typings.backups.constrained_strings import (
    BackupObjectKey,
    BackupObjectPrefix,
)
from app.schemas.typings.platform.strings import LocalFilePath


class BackupBucketClientContract(ClientContract, Protocol):
    """The off-site bucket (S3-compatible, EU) that keeps the archives."""

    def upload_file(self, key: BackupObjectKey, source: LocalFilePath) -> None:
        """Store the file under the key, streaming (any size)."""
        raise NotImplementedError

    def download_file(self, key: BackupObjectKey, target: LocalFilePath) -> bool:
        """Write the object to the file; False when there is no such object."""
        raise NotImplementedError

    def list_objects(self, prefix: BackupObjectPrefix) -> list[BackupObjectListing]:
        """Every object under the prefix (all pages), in key order."""
        raise NotImplementedError

    def delete_object(self, key: BackupObjectKey) -> None:
        """Delete the object; a missing object is not an error."""
        raise NotImplementedError


class BackupCipherAdapterContract(AdapterContract, Protocol):
    """Archive encryption (age): to the public keys, from the private one."""

    def encrypt_file(self, source: LocalFilePath, target: LocalFilePath) -> None:
        raise NotImplementedError

    def decrypt_file(self, source: LocalFilePath, target: LocalFilePath) -> None:
        """
        Raises:
            BackupArchiveCorruptError: not for this identity, or changed.
            ValidationFailedError: no identity is configured.
        """
        raise NotImplementedError


class DatabaseDumpAdapterContract(AdapterContract, Protocol):
    def dump(self, target: LocalFilePath) -> DatabaseFacts:
        """
        Write a custom-format dump of the database to the file and return
        the facts of the very snapshot it dumped.

        Raises:
            BackupToolError: pg_dump or the database failed.
        """
        raise NotImplementedError


class ScratchDatabaseAdapterContract(AdapterContract, Protocol):
    def restore_and_inspect(
        self,
        archive: LocalFilePath,
        is_kept: IsScratchDatabaseKept,
    ) -> RestoredDatabase:
        """
        Restore the dump into a new scratch database, count it and probe
        its row-level security; drop it again unless it is kept.

        Raises:
            BackupToolError: the scratch database or pg_restore failed.
        """
        raise NotImplementedError
