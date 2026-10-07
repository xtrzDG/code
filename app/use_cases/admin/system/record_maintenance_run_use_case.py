from typed_time_provider import Microseconds, WallClock

from app.contracts.monitoring import MaintenanceRunRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.dto.admin_system import MaintenanceRunView
from app.schemas.dto.maintenance_runs import RecordMaintenanceRunCommand
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.use_cases.admin.system.system_views import maintenance_run_view


class RecordMaintenanceRunUseCase(
    UseCaseContract[RecordMaintenanceRunCommand, MaintenanceRunView]
):
    """
    `workshop backup` and `workshop restore-check` record how each run
    ended (with the release that ran it), so the admin system page shows
    the last backup and drill and whether a backup is overdue. The
    commands' own Sentry Crons monitors page when a run never comes.
    """

    def __init__(
        self,
        maintenance_run_repo: MaintenanceRunRepoContract,
        release: ReleaseVersion | None,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._maintenance_run_repo: MaintenanceRunRepoContract = maintenance_run_repo
        self._release: ReleaseVersion | None = release
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RecordMaintenanceRunCommand) -> MaintenanceRunView:
        now: Microseconds = self._wall_clock.now_unix()
        run = MaintenanceRunDocument(
            kind=input_data.kind,
            outcome=input_data.outcome,
            started_at=input_data.started_at,
            finished_at=input_data.finished_at,
            archive_key=input_data.archive_key,
            archive_size=input_data.archive_size,
            row_count=input_data.row_count,
            error=input_data.error,
            release=self._release,
            created_at=now,
            updated_at=now,
        )
        self._maintenance_run_repo.record(run)
        return maintenance_run_view(run)
