"""
A world where Meta browns out: the channels testbed's outbox behind the
provider circuit breakers and the outbound bulkhead, sent by a worker with
the production lanes (4 outbound threads, 1 ops thread), Meta's Graph API
on a transport that hangs, fails or answers as the test says, and Telegram
(the businesses' bots and the platform bot) on one that always answers.
"""

import httpx

from app.adapters.channels.circuit_breaking_channel_adapter import (
    CircuitBreakingChannelAdapter,
)
from app.adapters.channels.circuit_breaking_whatsapp_template_adapter import (
    CircuitBreakingWhatsAppTemplateAdapter,
)
from app.adapters.channels.telegram_channel_adapter import TelegramChannelAdapter
from app.adapters.channels.whatsapp_channel_adapter import WhatsAppChannelAdapter
from app.adapters.notifications.circuit_breaking_telegram_bot_adapter import (
    CircuitBreakingTelegramBotAdapter,
)
from app.clients.meta.meta_graph_client import MetaGraphClient
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.contracts.channels import ChannelAdapterContract
from app.contracts.jobs import QueuedJobOperator
from app.facilitators.notifications.staff_notification_sender_facilitator import (
    StaffNotificationSenderFacilitator,
)
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.facilitators.resilience.outbound_bulkhead_facilitator import (
    OutboundBulkheadFacilitator,
)
from app.gateways.worker.background_worker import BackgroundWorker
from app.orchestrators.channels.outbox.deliver_outbound_message_orchestrator import (
    DeliverOutboundMessageOrchestrator,
)
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.resilience import OutboundProvider
from app.schemas.dto.platform_alerts import PlatformAlertDelivery
from app.schemas.typings.handoffs.strings import ManagerContactAddress
from app.schemas.typings.monitoring.strings import PlatformAlertMessage
from app.schemas.typings.platform.constrained_integers import (
    WorkerLaneConcurrency,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.use_cases.admin.alerts.check_platform_alerts_use_case import (
    SEND_PLATFORM_ALERT_JOB,
)
from app.use_cases.admin.alerts.send_platform_alert_use_case import (
    SendPlatformAlertUseCase,
)
from app.use_cases.channels.outbox.send_outbound_message_use_case import (
    SendOutboundMessageUseCase,
)
from app.utilities.deliveries.delivery_jobs import DELIVER_OUTBOUND_JOB
from app.utilities.jobs.platform_alert_lane import platform_alert_lane
from app.utilities.resilience.provider_circuits import (
    guarded_circuits,
    provider_circuit,
    provider_slots_of_lane,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.channels.channels_deliveries import as_job_operator
from tests.channels.channels_settings import PLATFORM_BOT_TOKEN
from tests.channels.testbed import ChannelsTestbed
from tests.resilience.provider_fakes import (
    AnsweringTelegram,
    BrownOutMeta,
    CircuitStates,
    MetaMode,
)
from tests.resilience.test_circuit_breaker import Ticks

OUTBOUND_THREADS: WorkerLaneConcurrency = WorkerLaneConcurrency(4)
PRODUCTION_LANES: dict[JobLane, WorkerLaneConcurrency] = {
    JobLane.INBOUND: WorkerLaneConcurrency(1),
    JobLane.OUTBOUND: OUTBOUND_THREADS,
    JobLane.DEFAULT: WorkerLaneConcurrency(1),
    JobLane.AUTOTESTS: WorkerLaneConcurrency(1),
    JobLane.OPS: WorkerLaneConcurrency(1),
}
META: CircuitName = provider_circuit(OutboundProvider.META)
ALERT_CHAT: str = "-1001234567890"


class SendBulkheadsWorld(ChannelsTestbed):
    """The outbox and the platform alerts behind the provider guards."""

    def __init__(self, meta_mode: MetaMode = MetaMode.HANG) -> None:
        super().__init__()
        self.ticks = Ticks()
        self.circuit_states = CircuitStates()
        self.circuit_breaker = CircuitBreakerFacilitator(
            self.ticks.clock(),
            metrics=self.circuit_states,
            known_circuits=guarded_circuits(),
        )
        self.meta = BrownOutMeta(meta_mode)
        self.telegram = AnsweringTelegram()
        meta_client = MetaGraphClient(transport=httpx.MockTransport(self.meta.handle))
        bot_client = TelegramBotClient(
            transport=httpx.MockTransport(self.telegram.handle)
        )
        whatsapp = WhatsAppChannelAdapter(
            meta_client,
            self.phone_number_parser,
            self.settings,
            text_resolver=self.text_resolver,
        )
        templates = CircuitBreakingWhatsAppTemplateAdapter(
            whatsapp, self.circuit_breaker, META
        )
        staff_sender = StaffNotificationSenderFacilitator(
            CircuitBreakingTelegramBotAdapter(
                bot_client,
                self.circuit_breaker,
                provider_circuit(OutboundProvider.PLATFORM_BOT),
            ),
            templates,
            self.settings,
        )
        self.guarded_send = SendOutboundMessageUseCase(
            self.guard(
                TelegramChannelAdapter(
                    bot_client, self.phone_number_parser, self.settings
                ),
                OutboundProvider.TELEGRAM,
            ),
            self.guard(whatsapp, OutboundProvider.META),
            self.guard(self.messenger_adapter, OutboundProvider.META),
            self.guard(self.instagram_adapter, OutboundProvider.META),
            self.channel_repo,
            self.secret_cipher,
            staff_sender,
            self.push_sender,
            self.usage_event_repo,
            self.wall_clock,
            templates,
            self.billing_attachments,
            OutboundBulkheadFacilitator(provider_slots_of_lane(OUTBOUND_THREADS)),
        )
        self.send_platform_alert = SendPlatformAlertUseCase(staff_sender)

    def guard(
        self,
        adapter: ChannelAdapterContract,
        provider: OutboundProvider,
    ) -> CircuitBreakingChannelAdapter:
        return CircuitBreakingChannelAdapter(
            adapter, self.circuit_breaker, provider_circuit(provider)
        )

    def guarded_worker(self) -> BackgroundWorker:
        """A worker with the production lanes over the guarded senders."""

        operators: dict[JobName, QueuedJobOperator] = {
            DELIVER_OUTBOUND_JOB: as_job_operator(
                DeliverOutboundMessageOrchestrator(
                    self.take_due_outbound_message,
                    self.guarded_send,
                    self.record_outbound_attempt,
                    self.build_undelivered_reply_handoff,
                    self.handoffs_to_human,
                )
            ),
            SEND_PLATFORM_ALERT_JOB: as_job_operator(
                UseCaseOrchestrator(self.send_platform_alert)
            ),
        }
        return BackgroundWorker(
            periodic_jobs=[],
            queued_job_operators=operators,
            job_repo=self.jobs.job_repo,
            periodic_run_repo=self.jobs.periodic_run_repo,
            wall_clock=self.wall_clock,
            error_reporter=self.worker_errors,
            poll_seconds=WorkerPollSeconds(5),
            storage_scope=StorageScopeContext(),
            job_wakeup=self.jobs.job_wakeup,
            lane_concurrency=PRODUCTION_LANES,
        )

    def queue_platform_alert(self, text: str) -> None:
        """One alert to the team's Telegram chat, in the alerts' lane."""

        self.job_queue.enqueue(
            SEND_PLATFORM_ALERT_JOB,
            JobPayloadJson(
                PlatformAlertDelivery(
                    channel=ManagerContactChannel.TELEGRAM,
                    address=ManagerContactAddress(ALERT_CHAT),
                    text=PlatformAlertMessage(text),
                ).model_dump_json()
            ),
            None,
            lane=platform_alert_lane(),
            serial_key=JobSerialKey(f"platform_alert:telegram:{ALERT_CHAT}"),
        )

    def platform_bot_sends(self) -> int:
        return self.telegram.sent_with.count(PLATFORM_BOT_TOKEN)
