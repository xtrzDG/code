"""The channels testbed's inbox and outbox use cases."""

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.facilitators.notifications.manager_notification_facilitator import (
    ManagerNotificationFacilitator,
)
from app.facilitators.notifications.push_notification_sender_facilitator import (
    PushNotificationSenderFacilitator,
)
from app.facilitators.notifications.staff_delivery_recorder_facilitator import (
    StaffDeliveryRecorderFacilitator,
)
from app.facilitators.notifications.staff_notification_sender_facilitator import (
    StaffNotificationSenderFacilitator,
)
from app.registries.limits.request_rate_limit_registry import (
    RequestRateLimitRegistry,
)
from app.schemas.configurations.app_settings import AppSettings
from app.use_cases.channels.inbox.accept_platform_bot_update_use_case import (
    AcceptPlatformBotUpdateUseCase,
)
from app.use_cases.channels.inbox.claim_inbound_event_use_case import (
    ClaimInboundEventUseCase,
)
from app.use_cases.channels.inbox.finish_inbound_event_use_case import (
    FinishInboundEventUseCase,
)
from app.use_cases.channels.inbox.read_accepted_post_call_use_case import (
    ReadAcceptedPostCallUseCase,
)
from app.use_cases.channels.inbox.recall_inbound_reply_use_case import (
    RecallInboundReplyUseCase,
)
from app.use_cases.channels.inbox.release_inbound_event_use_case import (
    ReleaseInboundEventUseCase,
)
from app.use_cases.channels.inbox.store_inbound_messages_use_case import (
    StoreInboundMessagesUseCase,
)
from app.use_cases.channels.inbox.store_post_call_report_use_case import (
    StorePostCallReportUseCase,
)
from app.use_cases.channels.outbox.build_undelivered_reply_handoff_use_case import (
    BuildUndeliveredReplyHandoffUseCase,
)
from app.use_cases.channels.outbox.record_outbound_attempt_use_case import (
    RecordOutboundAttemptUseCase,
)
from app.use_cases.channels.outbox.send_outbound_message_use_case import (
    SendOutboundMessageUseCase,
)
from app.use_cases.channels.outbox.take_due_outbound_message_use_case import (
    TakeDueOutboundMessageUseCase,
)
from app.use_cases.widget.queue_widget_message_use_case import (
    QueueWidgetMessageUseCase,
)
from tests.channels.channels_use_cases import ChannelsUseCases
from tests.invoicing.attachment_fakes import StaticBillingAttachments
from tests.notifications.staff_alert_fakes import push_subscription_repo
from tests.notifications.web_push_fakes import (
    FakeWebPushClient,
    staff_delivery_state_repo,
)

# Retries come exactly after the base backoff (no jitter) in these tests.
NO_JITTER: float = 0.5


class ChannelsInbox(ChannelsUseCases):
    """Webhook intake into the inbox and the steps of the worker's jobs."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        super().__init__(settings)
        self.staff_sender = StaffNotificationSenderFacilitator(
            self.telegram_client, self.whatsapp_adapter, self.settings
        )
        self.push_subscription_repo = push_subscription_repo()
        self.staff_delivery_state_repo = staff_delivery_state_repo()
        self.delivery_recorder = StaffDeliveryRecorderFacilitator(
            self.staff_delivery_state_repo, self.push_subscription_repo
        )
        self.rate_limits = RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter())
        self.web_push_client = FakeWebPushClient()
        self.push_sender = PushNotificationSenderFacilitator(
            self.push_subscription_repo, self.web_push_client
        )
        self.staff_notifier = ManagerNotificationFacilitator(
            self.outbound_message_repo,
            self.job_queue,
            self.settings,
            self.rate_limits,
            self.delivery_recorder,
            self.wall_clock,
        )
        self.store_inbound_messages = StoreInboundMessagesUseCase(
            self.inbound_event_repo, self.job_queue, self.channel_repo, self.wall_clock
        )
        self.accept_platform_bot_update = AcceptPlatformBotUpdateUseCase(
            self.inbound_event_repo, self.job_queue, self.settings, self.wall_clock
        )
        self.store_post_call_report = StorePostCallReportUseCase(
            self.inbound_event_repo, self.job_queue, self.wall_clock
        )
        self.queue_widget_message = QueueWidgetMessageUseCase(
            self.inbound_event_repo, self.job_queue, self.wall_clock
        )
        self.claim_inbound_event = ClaimInboundEventUseCase(
            self.inbound_event_repo, self.job_queue, self.wall_clock
        )
        self.recall_inbound_reply = RecallInboundReplyUseCase(self.message_repo)
        self.finish_inbound_event = FinishInboundEventUseCase(
            self.inbound_event_repo,
            self.outbound_message_repo,
            self.job_queue,
            self.wall_clock,
            self.channel_repo,
        )
        self.release_inbound_event = ReleaseInboundEventUseCase(
            self.inbound_event_repo, self.wall_clock
        )
        self.read_accepted_post_call = ReadAcceptedPostCallUseCase(
            self.voice_webhook_adapter
        )
        self.take_due_outbound_message = TakeDueOutboundMessageUseCase(
            self.outbound_message_repo, self.job_queue, self.wall_clock
        )
        self.billing_attachments = StaticBillingAttachments()
        self.send_outbound_message = SendOutboundMessageUseCase(
            self.telegram_adapter,
            self.whatsapp_adapter,
            self.messenger_adapter,
            self.instagram_adapter,
            self.channel_repo,
            self.secret_cipher,
            self.staff_sender,
            self.push_sender,
            self.usage_event_repo,
            self.wall_clock,
            self.whatsapp_adapter,
            self.billing_attachments,
        )
        self.record_outbound_attempt = RecordOutboundAttemptUseCase(
            self.outbound_message_repo,
            self.job_queue,
            self.channel_repo,
            self.handoff_repo,
            self.live_events,
            self.delivery_recorder,
            self.feedback_request_repo,
            jitter=lambda: NO_JITTER,
        )
        self.build_undelivered_reply_handoff = BuildUndeliveredReplyHandoffUseCase(
            self.business_repo, self.conversation_repo
        )
