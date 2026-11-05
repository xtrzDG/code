"""
The API's pipeline watchdog wired in memory: the worker pulses, the job
queue, the alert states and the watchers' marks, one shared lock, a clock
the test moves and staff providers that record what they send.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.facilitators.monitoring.direct_platform_alert_facilitator import (
    DirectPlatformAlertFacilitator,
)
from app.registries.locks.platform_alert_lock_registry import (
    PlatformAlertLockRegistry,
)
from app.schemas.configurations.platform_alert_settings import PlatformAlertSettings
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.outbound_messages import OutboundTemplate
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.exceptions.application_errors import DeliveryNotConfiguredError
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.monitoring.constrained_integers import (
    AlertCooldownMinutes,
    PipelineWatchdogSeconds,
)
from app.schemas.typings.monitoring.constrained_strings import (
    AlertChatId,
    MonitorHolderName,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.use_cases.admin.alerts.watch_pipeline_use_case import WatchPipelineUseCase
from tests.platform_ops.ops_documents import job, pulse
from tests.platform_ops.ops_world import CABINET, OpsWorld

API_ONE: MonitorHolderName = MonitorHolderName("srv-api-1:101")
API_TWO: MonitorHolderName = MonitorHolderName("srv-api-2:202")
CHAT: AlertChatId = AlertChatId("-1001234567890")
ONCALL: EmailAddress = EmailAddress("oncall@workshop.example")
INTERVAL: PipelineWatchdogSeconds = PipelineWatchdogSeconds(60)


class RecordingStaffSender:
    """The platform bot and SMTP: records every part, or refuses a channel."""

    def __init__(self, refused_channels: Sequence[str] = ()) -> None:
        self.sent: list[tuple[str, str]] = []
        self._refused: set[str] = set(refused_channels)

    def split(self, contact: ManagerContact, text: MessageText) -> list[MessageText]:
        del contact
        return [text]

    def send(
        self,
        contact: ManagerContact,
        text: MessageText,
        template: OutboundTemplate | None,
    ) -> ProviderMessageId | None:
        assert template is None
        if contact.channel.value in self._refused:
            raise DeliveryNotConfiguredError("No platform bot token.")
        self.sent.append((contact.channel.value, str(text)))
        return None

    def send_with_files(
        self,
        contact: ManagerContact,
        text: MessageText,
        attachments: Sequence[EmailAttachment],
    ) -> None:
        raise AssertionError("Platform alerts carry no files.")

    def headlines(self) -> list[str]:
        return [text.splitlines()[0] for _, text in self.sent]


class WatchWorld(OpsWorld):
    """OpsWorld (pulses, jobs, alert states, marks, lock) plus the watchdog."""

    def __init__(self, cooldown_minutes: int = 60) -> None:
        super().__init__()
        self.sender = RecordingStaffSender()
        self.settings = PlatformAlertSettings(
            telegram_chat_ids=[CHAT],
            emails=[ONCALL],
            cooldown_minutes=AlertCooldownMinutes(cooldown_minutes),
            watchdog_seconds=INTERVAL,
        )

    def watchdog(
        self,
        holder: MonitorHolderName = API_ONE,
        locks: PlatformAlertLockRegistry | None = None,
    ) -> WatchPipelineUseCase:
        return WatchPipelineUseCase(
            locks=self.locks if locks is None else locks,
            monitor_repo=self.monitor_repo,
            state_repo=self.alert_state_repo,
            worker_heartbeat_repo=self.heartbeat_repo,
            system_health_repo=self.health_repo,
            direct_alerts=DirectPlatformAlertFacilitator(self.sender, self.settings),
            alert_settings=self.settings,
            holder=holder,
            interval=INTERVAL,
            release=None,
            cabinet_base_url=CABINET,
            wall_clock=self.clock.wall_clock,
        )

    def worker_beats(self, host: str = "srv-worker-1") -> None:
        """A worker writes its pulse now."""

        beat = pulse(host, Microseconds(self.clock.now))
        self.pulses.upsert(str(beat.id), beat)

    def customer_waits_since(self, seconds_ago: int) -> None:
        """A customer message is due on the inbound lane since then."""

        waiting = job(
            QueuedJobStatus.PENDING,
            JobLane.INBOUND,
            Microseconds(self.clock.now - seconds_ago * 1_000_000),
            name="process_inbound_message",
        )
        self.jobs.upsert(str(waiting.id), waiting)
