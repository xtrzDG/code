"""The storage and the ledger copy of a business's deletion, chosen by the settings."""

import logging

from typed_time_provider import Microseconds, WallClock

from app.adapters.business_closures.bucket_deletion_ledger_mirror_adapter import (
    BucketDeletionLedgerMirrorAdapter,
)
from app.adapters.business_closures.in_memory_deletion_ledger_mirror_adapter import (
    InMemoryDeletionLedgerMirrorAdapter,
)
from app.adapters.storage.in_memory_business_row_eraser_adapter import (
    InMemoryBusinessRowEraserAdapter,
)
from app.adapters.storage.in_memory_collection_registry import (
    InMemoryCollectionRegistry,
)
from app.adapters.storage.postgres.postgres_business_row_eraser_adapter import (
    PostgresBusinessRowEraserAdapter,
)
from app.clients.object_storage.s3_backup_bucket_client import S3BackupBucketClient
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.contracts.business_erasure import (
    BusinessRowEraserAdapterContract,
    DeletionLedgerMirrorAdapterContract,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment

logger: logging.Logger = logging.getLogger(__name__)


def build_business_row_eraser(
    connection_pools: PostgresConnectionPools | None,
    registry: InMemoryCollectionRegistry,
) -> BusinessRowEraserAdapterContract:
    """Every table through the platform pool with a database; else in memory."""

    if connection_pools is None:
        return InMemoryBusinessRowEraserAdapter(registry)

    return PostgresBusinessRowEraserAdapter(connection_pools)


def build_deletion_ledger_mirror(
    settings: AppSettings,
) -> DeletionLedgerMirrorAdapterContract:
    """
    The ledger's copy in the backup bucket (BACKUP_S3_*); without backups
    there is no backup to restore either, so the process keeps it.
    """

    bucket = settings.backup.bucket
    if bucket is None:
        if settings.environment is DeploymentEnvironment.PRODUCTION:
            logger.warning(
                "BACKUP_S3_* is not set: the deletion ledger has no copy outside "
                "the database."
            )
        return InMemoryDeletionLedgerMirrorAdapter()

    return BucketDeletionLedgerMirrorAdapter(
        S3BackupBucketClient(
            connection=bucket,
            wall_clock=WallClock(preferred_time_unit_type=Microseconds),
        ),
        settings.backup.prefix,
    )
