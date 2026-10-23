"""
Adapters of how the processes work together on one database: readiness,
storage transactions and the job queue's wake-ups between processes.
"""

from dependency_injector import containers
from dependency_injector.providers import Callable, DependenciesContainer, Singleton

from app.adapters.health.database_probe_factory import build_database_probe_adapter
from app.adapters.jobs.job_wakeup_adapter_factory import build_job_wakeup_adapter
from app.adapters.storage.data_task_batch_adapter_factory import (
    build_data_task_batch_adapter,
)
from app.adapters.storage.database_role_inspection_factory import (
    build_database_role_inspection_adapter,
)
from app.adapters.storage.postgres.connection_pools_factory import (
    application_database_url,
)
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    BUILD_MIGRATIONS_DIRECTORY,
    SqlFileMigrationSourceAdapter,
)
from app.adapters.storage.unit_of_work_factory import (
    build_read_session_adapter,
    build_unit_of_work_adapter,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.data_tasks import DataTaskBatchAdapterContract
from app.contracts.database_roles import DatabaseRoleInspectionAdapterContract
from app.contracts.health import DatabaseProbeAdapterContract
from app.contracts.jobs import JobWakeupContract
from app.contracts.storage import StorageReadSessionContract, StorageUnitOfWorkContract


class ProcessAdaptersContainer(containers.DeclarativeContainer):
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Readiness (GET /readyz): the database probe over the tenant pool and
    # the migration files of this build.
    database_probe: Singleton[DatabaseProbeAdapterContract] = Singleton(
        build_database_probe_adapter,
        connection_pools=clients.postgres_pools,
    )
    # The login roles of the pools, checked at startup (none in memory).
    database_roles: Singleton[DatabaseRoleInspectionAdapterContract] = Singleton(
        build_database_role_inspection_adapter,
        connection_pools=clients.postgres_pools,
    )
    migration_source: Singleton[SqlFileMigrationSourceAdapter] = Singleton(
        SqlFileMigrationSourceAdapter,
        migrations_directory=BUILD_MIGRATIONS_DIRECTORY,
    )
    # One storage transaction for a block (Postgres), None in memory.
    storage_unit_of_work: Singleton[StorageUnitOfWorkContract | None] = Singleton(
        build_unit_of_work_adapter,
        connection_pools=clients.postgres_pools,
        storage_scope=utilities.storage_scope,
    )
    # Several reads in one transaction (Postgres), None in memory.
    storage_read_session: Singleton[StorageReadSessionContract | None] = Singleton(
        build_read_session_adapter,
        connection_pools=clients.postgres_pools,
        storage_scope=utilities.storage_scope,
    )
    # Queued jobs wake idle lane threads at once: Postgres NOTIFY/LISTEN
    # reaches the worker processes, the in-process signal without a database.
    job_wakeup: Singleton[JobWakeupContract] = Singleton(
        build_job_wakeup_adapter,
        connection_pool=clients.postgres_platform_pool,
        database_url=Callable(application_database_url, settings=config.app_settings),
        listen_database_url=config.app_settings.provided.live_events_database_url,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # One keyset batch of a post-deploy data task (Postgres; nothing to do
    # in memory).
    data_task_batches: Singleton[DataTaskBatchAdapterContract] = Singleton(
        build_data_task_batch_adapter,
        connection_pool=clients.postgres_platform_pool,
    )
