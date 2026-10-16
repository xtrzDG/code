"""
The platform's operations on a real database: the system page reads the
database's size from the catalog, and the backup commands record their runs
through the application container on DATABASE_URL.
"""

from app.adapters.monitoring.database_size_adapter_factory import (
    UnmeasuredDatabaseSizeAdapter,
    build_database_size_adapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.gateways.cli.maintenance_run_log import record_with_container
from app.repositories.maintenance_run_repository import MaintenanceRunRepository
from app.schemas.constants.monitoring import MaintenanceRunKind, MaintenanceRunOutcome
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.dto.maintenance_runs import RecordMaintenanceRunCommand
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.platform_ops.ops_documents import MINUTE, at
from tests.storage.conftest import PostgresCollectionFactory


def test_the_database_size_comes_from_the_catalog(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    size = build_database_size_adapter(connection_pool).measure()

    assert size is not None
    tables = {str(table.table): table for table in size.tables}
    assert "workshop.messages" in tables and "workshop.incidents" in tables
    assert int(size.total_bytes) >= sum(int(t.total_bytes) for t in size.tables)
    assert all(int(table.row_estimate) >= 0 for table in size.tables)
    assert build_database_size_adapter(None).measure() is None
    assert isinstance(build_database_size_adapter(None), UnmeasuredDatabaseSizeAdapter)


def test_a_command_records_its_run_on_the_database(
    database_url: DatabaseUrl,
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    settings = assemble_app_settings(
        {"APP_ENV": "test", "DATABASE_URL": str(database_url)}
    )

    record_with_container(
        settings,
        RecordMaintenanceRunCommand(
            kind=MaintenanceRunKind.RESTORE_DRILL,
            outcome=MaintenanceRunOutcome.SUCCEEDED,
            started_at=at(-10 * MINUTE),
            finished_at=at(0),
        ),
    )

    runs = MaintenanceRunRepository(
        postgres_collections(MaintenanceRunDocument, "maintenance_runs")
    )
    with storage_scope.platform_wide():
        latest = runs.find_latest(MaintenanceRunKind.RESTORE_DRILL)
    assert latest is not None
    assert latest.outcome is MaintenanceRunOutcome.SUCCEEDED
    assert int(latest.finished_at) == int(at(0))
