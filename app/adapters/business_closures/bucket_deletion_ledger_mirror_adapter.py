import tempfile
from pathlib import Path

from pydantic import ValidationError

from app.contracts.backups import BackupBucketClientContract
from app.contracts.business_erasure import DeletionLedgerMirrorAdapterContract
from app.schemas.dto.backups import BackupObjectListing
from app.schemas.dto.business_closures.deletion_ledger import DeletionLedgerRecord
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.backups.constrained_strings import (
    BackupObjectKey,
    BackupObjectPrefix,
)
from app.schemas.typings.platform.strings import LocalFilePath

LEDGER_FOLDER: str = "deletion-ledger/"
RECORD_SUFFIX: str = ".json"


class BucketDeletionLedgerMirrorAdapter(DeletionLedgerMirrorAdapterContract):
    """
    The deletion ledger's copy in the backup bucket, one small JSON object
    per deleted business (`<prefix>deletion-ledger/<business id>.json`):
    outside the database and its backups, so whichever backup is restored,
    the drill knows every business deleted since. Backup retention only
    ever removes archives it recognizes, never these.
    """

    def __init__(
        self, bucket: BackupBucketClientContract, prefix: BackupObjectPrefix
    ) -> None:
        self._bucket: BackupBucketClientContract = bucket
        self._folder: BackupObjectPrefix = BackupObjectPrefix(
            f"{prefix}{LEDGER_FOLDER}"
        )

    def record(self, record: DeletionLedgerRecord) -> None:
        key = BackupObjectKey(f"{self._folder}{record.business_id}{RECORD_SUFFIX}")
        with tempfile.TemporaryDirectory(prefix="workshop-ledger-") as directory:
            path: Path = Path(directory) / "record.json"
            path.write_text(record.model_dump_json(), encoding="utf-8")
            self._bucket.upload_file(key, LocalFilePath(str(path)))

    def read_all(self) -> list[DeletionLedgerRecord]:
        listings: list[BackupObjectListing] = self._bucket.list_objects(self._folder)
        records: list[DeletionLedgerRecord] = []
        with tempfile.TemporaryDirectory(prefix="workshop-ledger-") as directory:
            for index, listing in enumerate(listings):
                if not str(listing.key).endswith(RECORD_SUFFIX):
                    continue

                path: Path = Path(directory) / f"{index}.json"
                if self._bucket.download_file(listing.key, LocalFilePath(str(path))):
                    records.append(read_record(path, listing.key))

        return sorted(records, key=lambda record: int(record.started_at))


def read_record(path: Path, key: BackupObjectKey) -> DeletionLedgerRecord:
    try:
        return DeletionLedgerRecord.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except ValidationError as error:
        raise ExternalServiceError(
            f"The deletion ledger object {key} is not a ledger record."
        ) from error
