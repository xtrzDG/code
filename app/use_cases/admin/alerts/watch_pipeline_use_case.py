import logging
from collections.abc import Mapping

from typed_time_provider import Microseconds, WallClock

from app.contracts.health import WorkerHeartbeatRepoContract
from app.contracts.monitoring import (
    DirectPlatformAlertFacilitatorContract,
    PlatformAlertLockRegistryContract,
    PlatformAlertStateRepoContract,
    PlatformMonitorRepoContract,
    SystemHealthRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.platform_alert_settings import PlatformAlertSettings
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.monitoring import (
    AlertNoticeKind,
    PlatformAlertCode,
    PlatformMonitor,
)
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.dto.pipeline_health import (
    PipelineHealthReport,
    PipelineWatchReport,
    PipelineWatchTick,
)
from app.schemas.dto.platform_alerts import PlatformAlertRule
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.monitoring.constrained_integers import (
    NotificationCount,
    PipelineWatchdogSeconds,
)
from app.schemas.typings.monitoring.constrained_strings import MonitorHolderName
from app.schemas.typings.platform.constrained_strings import (
    CabinetBaseUrl,
    ReleaseVersion,
)
from app.use_cases.admin.alerts.alert_episodes import next_episode_step
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from app.use_cases.admin.alerts.alert_texts import compose_alert_message
from app.use_cases.admin.alerts.pipeline_alert_checks import (
    PIPELINE_ALERT_CODES,
    pipeline_observations,
)
from app.use_cases.admin.alerts.watchdog_lease import may_lead, renewed_lease
from app.utilities.monitoring.pipeline_health import assess_pipeline

logger: logging.Logger = logging.getLogger(__name__)
type Notice = tuple[PlatformAlertStateDocument, AlertNoticeKind]


class WatchPipelineUseCase(UseCaseContract[PipelineWatchTick, PipelineWatchReport]):
    """
    The API's pipeline watchdog: one look every PIPELINE_WATCHDOG_SECONDS
    in each API process, outside the workers it watches.

    Under the alert-state lock the process first checks that it leads
    (`watchdog_lease.py`: the lease in the watchdog's mark); only the
    leader reads the pipeline (the freshest worker pulse, the oldest due
    customer message), steps the WORKER_DOWN and INBOUND_BACKLOG episodes
    with the same cooldown as the workers' `platform_alerts` job (their
    states are shared, so whichever looks first tells the team once) and
    renews its lease, all in one transaction. After the commit it sends
    the episode's message straight through the platform bot and SMTP
    (`DirectPlatformAlertFacilitator`): the job queue needs the very
    workers that are gone. A look that cannot take the lock (another
    process holds it, the database is down) leaves the turn to the next.
    """

    def __init__(
        self,
        locks: PlatformAlertLockRegistryContract,
        monitor_repo: PlatformMonitorRepoContract,
        state_repo: PlatformAlertStateRepoContract,
        worker_heartbeat_repo: WorkerHeartbeatRepoContract,
        system_health_repo: SystemHealthRepoContract,
        direct_alerts: DirectPlatformAlertFacilitatorContract,
        alert_settings: PlatformAlertSettings,
        holder: MonitorHolderName,
        interval: PipelineWatchdogSeconds,
        release: ReleaseVersion | None,
        cabinet_base_url: CabinetBaseUrl | None,
        wall_clock: WallClock[Microseconds],
        rules: Mapping[PlatformAlertCode, PlatformAlertRule] = PLATFORM_ALERT_RULES,
    ) -> None:
        self._locks: PlatformAlertLockRegistryContract = locks
        self._monitors: PlatformMonitorRepoContract = monitor_repo
        self._states: PlatformAlertStateRepoContract = state_repo
        self._heartbeats: WorkerHeartbeatRepoContract = worker_heartbeat_repo
        self._health: SystemHealthRepoContract = system_health_repo
        self._direct_alerts: DirectPlatformAlertFacilitatorContract = direct_alerts
        self._settings: PlatformAlertSettings = alert_settings
        self._holder: MonitorHolderName = holder
        self._interval: PipelineWatchdogSeconds = interval
        self._release: ReleaseVersion | None = release
        self._cabinet_base_url: CabinetBaseUrl | None = cabinet_base_url
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rules: Mapping[PlatformAlertCode, PlatformAlertRule] = rules

    def run(self, input_data: PipelineWatchTick) -> PipelineWatchReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        try:
            with self._locks.lock_states():
                mark = self._monitors.get(PlatformMonitor.PIPELINE_WATCHDOG)
                if not may_lead(mark, self._holder, now):
                    return PipelineWatchReport()

                report: PipelineHealthReport = self._read_pipeline(now)
                notices: list[Notice] = self._step_episodes(report, now)
                self._monitors.save(
                    renewed_lease(
                        mark, self._holder, self._interval, self._release, now
                    )
                )
        except ApplicationError as error:
            logger.warning("The pipeline watchdog skipped a look: %s", error)
            return PipelineWatchReport()

        # After the commit: the episodes are stored, so no other process
        # tells the team the same news, whatever happens to this send.
        sent: int = sum(int(self._send(state, notice)) for state, notice in notices)
        return PipelineWatchReport(
            is_leader=True,
            pipeline=report.status,
            sent_count=NotificationCount(sent),
        )

    def _read_pipeline(self, now: Microseconds) -> PipelineHealthReport:
        return assess_pipeline(
            self._heartbeats.find_freshest(),
            self._health.find_oldest_due_job(JobLane.INBOUND, now),
            int(self._health.count_due_jobs(JobLane.INBOUND, now)),
            now,
        )

    def _step_episodes(
        self, report: PipelineHealthReport, now: Microseconds
    ) -> list[Notice]:
        stored: dict[PlatformAlertCode, PlatformAlertStateDocument] = {
            state.code: state
            for state in self._states.get_many(list(PIPELINE_ALERT_CODES))
        }
        notices: list[Notice] = []
        for observation in pipeline_observations(report, self._rules):
            step = next_episode_step(
                stored.get(observation.code),
                observation,
                now,
                self._settings.cooldown_minutes,
            )
            if step is None:
                continue

            self._states.save(step.state)
            if step.notice is not None:
                notices.append((step.state, step.notice))

        return notices

    def _send(
        self, state: PlatformAlertStateDocument, notice: AlertNoticeKind
    ) -> NotificationCount:
        logger.warning(
            "Platform alert %s %s (pipeline watchdog): %s",
            state.code.value,
            notice.value,
            state.detail,
        )
        return self._direct_alerts.send(
            compose_alert_message(
                self._rules[state.code], state, notice, self._cabinet_base_url
            )
        )
