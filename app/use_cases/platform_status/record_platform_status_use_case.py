from typed_time_provider import Microseconds, WallClock

from app.contracts.monitoring import (
    PlatformAlertStateRepoContract,
    PlatformMonitorRepoContract,
)
from app.contracts.platform_status import (
    PlatformAnnouncementRepoContract,
    PlatformStatusDayRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.monitoring import PlatformAlertCode, PlatformMonitor
from app.schemas.domain.platform_status import PlatformStatusDayDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform_status.constrained_strings import StatusDay
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.platform_status.component_levels import current_levels
from app.use_cases.platform_status.monitoring_freshness import (
    is_monitoring_delayed,
    last_alert_check,
    with_monitoring_delay,
)
from app.use_cases.platform_status.status_history import fold_levels, status_day

ACTIVE_ANNOUNCEMENT_LIMIT: DocumentQueryLimit = DocumentQueryLimit(50)


class RecordPlatformStatusUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The `record_platform_status` periodic job (every five minutes, once per
    period across workers): every component's level now, from the alerts
    and the announcements in effect, folded into today's row of the
    status history, so a day shows the worst it was even after the alert
    is over. Hours whose alert checks were delayed (monitoring_freshness.py)
    are recorded as degraded for the chat channels, as the page showed
    them. The report counts the components recorded.
    """

    def __init__(
        self,
        alert_state_repo: PlatformAlertStateRepoContract,
        announcement_repo: PlatformAnnouncementRepoContract,
        status_day_repo: PlatformStatusDayRepoContract,
        monitor_repo: PlatformMonitorRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._alert_state_repo: PlatformAlertStateRepoContract = alert_state_repo
        self._monitor_repo: PlatformMonitorRepoContract = monitor_repo
        self._announcement_repo: PlatformAnnouncementRepoContract = announcement_repo
        self._status_day_repo: PlatformStatusDayRepoContract = status_day_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        now: Microseconds = self._wall_clock.now_unix()
        last_check = last_alert_check(
            self._monitor_repo.get(PlatformMonitor.ALERT_CHECKS)
        )
        levels = with_monitoring_delay(
            current_levels(
                self._alert_state_repo.get_many(list(PlatformAlertCode)),
                self._announcement_repo.list_active(ACTIVE_ANNOUNCEMENT_LIMIT),
                now,
            ),
            is_monitoring_delayed(last_check, now),
        )
        day: StatusDay = status_day(now)
        stored: list[PlatformStatusDayDocument] = self._status_day_repo.get_many([day])
        folded: PlatformStatusDayDocument = fold_levels(
            stored[0] if stored else None, day, levels, now
        )
        self._status_day_repo.save(folded)
        return JobReport(processed_count=ProcessedItemCount(len(folded.components)))
