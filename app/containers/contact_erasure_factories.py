"""The ledger of erased customers outside the database, chosen by the settings."""

import logging

from typed_time_provider import Microseconds, WallClock

from app.adapters.business_closures.bucket_contact_erasure_ledger_adapter import (
    BucketContactErasureLedgerAdapter,
)
from app.adapters.business_closures.in_memory_contact_erasure_ledger_adapter import (
    InMemoryContactErasureLedgerAdapter,
)
from app.clients.object_storage.s3_backup_bucket_client import S3BackupBucketClient
from app.contracts.contact_erasure_ledger import ContactErasureLedgerAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment

logger: logging.Logger = logging.getLogger(__name__)


def build_contact_erasure_ledger(
    settings: AppSettings,
) -> ContactErasureLedgerAdapterContract:
    """
    The ledger's copy in the backup bucket (BACKUP_S3_*), beside the
    deletion ledger of businesses; without backups there is no backup to
    restore either, so the process keeps it.
    """

    bucket = settings.backup.bucket
    if bucket is None:
        if settings.environment is DeploymentEnvironment.PRODUCTION:
            logger.warning(
                "BACKUP_S3_* is not set: erased customers have no ledger "
                "outside the database."
            )
        return InMemoryContactErasureLedgerAdapter()

    return BucketContactErasureLedgerAdapter(
        S3BackupBucketClient(
            connection=bucket,
            wall_clock=WallClock(preferred_time_unit_type=Microseconds),
        ),
        settings.backup.prefix,
    )
