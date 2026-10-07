"""
How `workshop backup` and `workshop restore-check` record their runs in the
database they serve (`maintenance_runs`), for the admin system page.

Only a command that has DATABASE_URL records: the backup always does (it
dumps that database); the restore drill does where it runs next to the
production database (the Render cron), not in CI, where it has only a
throwaway server. Recording is best effort: a database that refuses the
row is printed and the command's own outcome and exit code stand.
"""

from collections.abc import Callable
from typing import Protocol, TextIO, cast

from dependency_injector import providers

from app.containers.app import AppContainer
from app.contracts.operator_contract import OperatorContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.admin_system import MaintenanceRunView
from app.schemas.dto.maintenance_runs import RecordMaintenanceRunCommand
from app.schemas.typings.monitoring.strings import MaintenanceErrorText

type RecordRunOperator = OperatorContract[
    RecordMaintenanceRunCommand, MaintenanceRunView
]
type RecordRun = Callable[[AppSettings, RecordMaintenanceRunCommand], None]
# A failed run's reason is cut to one readable line.
MAX_ERROR_CHARACTERS: int = 500


class OverridableProvider(Protocol):
    def override(self, provider: object) -> object: ...


def record_with_container(
    settings: AppSettings,
    command: RecordMaintenanceRunCommand,
) -> None:
    """Record through the application container on DATABASE_URL."""

    container = AppContainer()
    cast(OverridableProvider, container.config.app_settings).override(
        providers.Object(settings)
    )
    try:
        operator: RecordRunOperator = (
            container.operators.platform_ops.record_maintenance_run_operator()
        )
        operator.operate(command)
    finally:
        connection_pool = container.clients.postgres_pool()
        if connection_pool is not None:
            connection_pool.close()


def record_maintenance_run(
    settings: AppSettings,
    command: RecordMaintenanceRunCommand,
    error_stream: TextIO,
    record: RecordRun = record_with_container,
) -> None:
    """Record the run when the command has the database; never raises."""

    if settings.database_url is None:
        return

    try:
        record(settings, command)
    except Exception as error:  # noqa: BLE001 - the command's outcome stands
        print(
            f"The run was not recorded for the system page: {error}",
            file=error_stream,
        )


def describe_failure(error: Exception) -> MaintenanceErrorText:
    """The first line of a failure, as the system page shows it."""

    lines: list[str] = str(error).strip().splitlines()
    first: str = lines[0] if lines else type(error).__name__
    return MaintenanceErrorText(first[:MAX_ERROR_CHARACTERS])
