"""
Adapters of how the processes work together on one database: readiness,
storage transactions and the job queue's wake-ups between processes.
"""

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.adapters.health.database_probe_factory import build_database_probe_adapter
from app.adapters.jobs.job_wakeup_adapter_factory import build_job_wakeup_adapter
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
from app.containers.utilities import UtilitiesContainer
from app.contracts.health import DatabaseProbeAdapterContract
from app.contracts.jobs import JobWakeupContract
from app.contracts.storage import StorageReadSessionContract, StorageUnitOfWorkContract


class ProcessAdaptersContainer(containers.DeclarativeContainer):
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Readiness (GET /readyz): the database probe over the shared pool and
    # the migration files of this build.
    database_probe: Singleton[DatabaseProbeAdapterContract] = Singleton(
        build_database_probe_adapter,
        connection_pool=clients.postgres_pool,
    )
    migration_source: Singleton[SqlFileMigrationSourceAdapter] = Singleton(
        SqlFileMigrationSourceAdapter,
        migrations_directory=BUILD_MIGRATIONS_DIRECTORY,
    )
    # One storage transaction for a block (Postgres), None in memory.
    storage_unit_of_work: Singleton[StorageUnitOfWorkContract | None] = Singleton(
        build_unit_of_work_adapter,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
    )
    # Several reads of one scope in one transaction (Postgres), None in memory.
    storage_read_session: Singleton[StorageReadSessionContract | None] = Singleton(
        build_read_session_adapter,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
    )
    # Queued jobs wake idle lane threads at once: Postgres NOTIFY/LISTEN
    # reaches the worker processes, the in-process signal without a database.
    job_wakeup: Singleton[JobWakeupContract] = Singleton(
        build_job_wakeup_adapter,
        connection_pool=clients.postgres_pool,
        database_url=config.app_settings.provided.database_url,
        listen_database_url=config.app_settings.provided.live_events_database_url,
    )
