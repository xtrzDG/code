import tempfile
from pathlib import Path

from pydantic import ValidationError

from app.contracts.backups import BackupBucketClientContract
from app.contracts.contact_erasure_ledger import ContactErasureLedgerAdapterContract
from app.schemas.dto.backups import BackupObjectListing
from app.schemas.dto.business_closures.contact_erasure_ledger import (
    ContactErasureRecord,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.backups.constrained_strings import (
    BackupObjectKey,
    BackupObjectPrefix,
)
from app.schemas.typings.platform.strings import LocalFilePath

CONTACTS_FOLDER: str = "deletion-ledger/contacts/"
# Not `.json`: the business ledger lists `deletion-ledger/` and reads only
# its own `.json` records, so it never mistakes an erasure for a deletion.
RECORD_SUFFIX: str = ".erasure"


class BucketContactErasureLedgerAdapter(ContactErasureLedgerAdapterContract):
    """
    The ledger of erased customers in the backup bucket, next to the
    deletion ledger of businesses and under the same key (put, get and
    list, no delete): one small JSON object per erased customer,
    `<prefix>deletion-ledger/contacts/<business id>/<contact id>.erasure`,
    holding ids and the moment only. Outside the database and its backups,
    so whichever backup is restored, the erasures since are known. Backup
    retention only ever removes archives it recognizes, never these.
    """

    def __init__(
        self, bucket: BackupBucketClientContract, prefix: BackupObjectPrefix
    ) -> None:
        self._bucket: BackupBucketClientContract = bucket
        self._folder: BackupObjectPrefix = BackupObjectPrefix(
            f"{prefix}{CONTACTS_FOLDER}"
        )

    def record(self, record: ContactErasureRecord) -> None:
        key = BackupObjectKey(
            f"{self._folder}{record.business_id}/{record.contact_id}{RECORD_SUFFIX}"
        )
        with tempfile.TemporaryDirectory(prefix="workshop-erasure-") as directory:
            path: Path = Path(directory) / "record.json"
            path.write_text(record.model_dump_json(), encoding="utf-8")
            self._bucket.upload_file(key, LocalFilePath(str(path)))

    def read_all(self) -> list[ContactErasureRecord]:
        listings: list[BackupObjectListing] = self._bucket.list_objects(self._folder)
        records: list[ContactErasureRecord] = []
        with tempfile.TemporaryDirectory(prefix="workshop-erasure-") as directory:
            for index, listing in enumerate(listings):
                if not str(listing.key).endswith(RECORD_SUFFIX):
                    continue

                path: Path = Path(directory) / f"{index}.json"
                if self._bucket.download_file(listing.key, LocalFilePath(str(path))):
                    records.append(read_record(path, listing.key))

        return sorted(records, key=lambda record: int(record.erased_at))


def read_record(path: Path, key: BackupObjectKey) -> ContactErasureRecord:
    try:
        return ContactErasureRecord.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except ValidationError as error:
        raise ExternalServiceError(
            f"The erasure ledger object {key} is not an erasure record."
        ) from error
