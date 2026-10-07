"""Files of one backup run in its work directory: digests and manifests."""

import hashlib
from pathlib import Path

from app.schemas.dto.backups import BackupManifest
from app.schemas.typings.backups.constrained_integers import BackupArchiveSize
from app.schemas.typings.backups.constrained_strings import BackupChecksum
from app.schemas.typings.platform.strings import LocalDirectoryPath, LocalFilePath

READ_BLOCK_SIZE: int = 1024 * 1024


def work_file(directory: LocalDirectoryPath, name: str) -> LocalFilePath:
    return LocalFilePath(str(Path(str(directory)) / name))


def file_digest(path: LocalFilePath) -> tuple[BackupChecksum, BackupArchiveSize]:
    """SHA-256 and size of a file, read in blocks."""

    digest = hashlib.sha256()
    size: int = 0
    with Path(str(path)).open("rb") as stream:
        while block := stream.read(READ_BLOCK_SIZE):
            digest.update(block)
            size += len(block)

    return BackupChecksum(digest.hexdigest()), BackupArchiveSize(size)


def write_manifest(manifest: BackupManifest, path: LocalFilePath) -> None:
    Path(str(path)).write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def read_manifest(path: LocalFilePath) -> BackupManifest:
    """The manifest in the file; ValueError (pydantic) when it is not one."""

    return BackupManifest.model_validate_json(
        Path(str(path)).read_text(encoding="utf-8")
    )


def remove_file(path: LocalFilePath) -> None:
    Path(str(path)).unlink(missing_ok=True)
