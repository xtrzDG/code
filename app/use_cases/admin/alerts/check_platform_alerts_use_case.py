import hashlib
import logging
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.monitoring import PlatformAlertStateRepoContract
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.platform_alert_settings import PlatformAlertSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.monitoring import AlertNoticeKind, PlatformAlertCode
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.platform_alerts import (
    AlertObservation,
    PlatformAlertDelivery,
    PlatformAlertRule,
)
from app.schemas.typings.handoffs.strings import ManagerContactAddress
from app.schemas.typings.monitoring.strings import PlatformAlertMessage
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import (
    CabinetBaseUrl,
    JobName,
    JobSerialKey,
)
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.admin.alerts.alert_checks import PlatformAlertChecks
from app.use_cases.admin.alerts.alert_episodes import EpisodeStep, next_episode_step
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from app.use_cases.admin.alerts.alert_texts import compose_alert_message

logger: logging.Logger = logging.getLogger(__name__)
SEND_PLATFORM_ALERT_JOB: JobName = JobName("send_platform_alert")


class CheckPlatformAlertsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The `platform_alerts` periodic job (every five minutes, once per period
    across workers): checks every rule of ops/alerts/*.yaml, keeps each
    alert's episode, and tells the team when an episode starts, again
    after PLATFORM_ALERT_COOLDOWN_MINUTES while it still fires, and once
    when it is over.

    Each message goes to every configured recipient (the platform bot's
    Telegram chats, e-mail) as its own `send_platform_alert` job in the
    outbound lane: the job queue retries it with backoff, so a provider
    outage delays an alert instead of losing it. The episode and its jobs
    are stored together (one transaction on Postgres), so a crash never
    marks an alert sent that was not queued. The report counts the
    messages queued.
    """

    def __init__(
        self,
        checks: PlatformAlertChecks,
        state_repo: PlatformAlertStateRepoContract,
        job_queue: JobQueueFacilitatorContract,
        alert_settings: PlatformAlertSettings,
        cabinet_base_url: CabinetBaseUrl | None,
        wall_clock: WallClock[Microseconds],
        unit_of_work: StorageUnitOfWorkContract | None = None,
        rules: Mapping[PlatformAlertCode, PlatformAlertRule] = PLATFORM_ALERT_RULES,
    ) -> None:
        self._checks: PlatformAlertChecks = checks
        self._state_repo: PlatformAlertStateRepoContract = state_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._settings: PlatformAlertSettings = alert_settings
        self._cabinet_base_url: CabinetBaseUrl | None = cabinet_base_url
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work
        self._rules: Mapping[PlatformAlertCode, PlatformAlertRule] = rules

    def run(self, input_data: JobTick) -> JobReport:
        now: Microseconds = self._wall_clock.now_unix()
        observations: list[AlertObservation] = self._checks.run(self._rules, now)
        stored: dict[PlatformAlertCode, PlatformAlertStateDocument] = {
            state.code: state for state in self._state_repo.get_many(list(self._rules))
        }
        queued: int = 0
        for observation in observations:
            step: EpisodeStep | None = next_episode_step(
                stored.get(observation.code),
                observation,
                now,
                self._settings.cooldown_minutes,
            )
            if step is None:
                continue

            with self._transaction():
                self._state_repo.save(step.state)
                if step.notice is not None:
                    queued += self._send(step.state, step.notice)

        return JobReport(processed_count=ProcessedItemCount(queued))

    def _send(self, state: PlatformAlertStateDocument, notice: AlertNoticeKind) -> int:
        message: PlatformAlertMessage = compose_alert_message(
            self._rules[state.code], state, notice, self._cabinet_base_url
        )
        logger.warning(
            "Platform alert %s %s: %s", state.code.value, notice.value, state.detail
        )
        recipients: list[tuple[ManagerContactChannel, str]] = [
            (ManagerContactChannel.TELEGRAM, str(chat_id))
            for chat_id in self._settings.telegram_chat_ids
        ] + [
            (ManagerContactChannel.EMAIL, str(email)) for email in self._settings.emails
        ]
        for channel, address in recipients:
            delivery = PlatformAlertDelivery(
                channel=channel,
                address=ManagerContactAddress(address),
                text=message,
            )
            self._job_queue.enqueue(
                SEND_PLATFORM_ALERT_JOB,
                JobPayloadJson(delivery.model_dump_json()),
                None,
                lane=JobLane.OUTBOUND,
                serial_key=recipient_serial_key(channel, address),
            )

        return len(recipients)

    def _transaction(self) -> AbstractContextManager[None]:
        if self._unit_of_work is None:
            return nullcontext()

        return self._unit_of_work.unit_of_work()


def recipient_serial_key(channel: ManagerContactChannel, address: str) -> JobSerialKey:
    """One recipient's alerts go out in order (a digest of the address, not it)."""

    digest: str = hashlib.sha256(f"{channel.value}:{address}".encode()).hexdigest()
    return JobSerialKey(f"platform_alert:{digest[:16]}")
