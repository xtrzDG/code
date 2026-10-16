"""The channels testbed's use cases and facilitators, wired over its infrastructure."""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.channels.acknowledge_telegram_taps_use_case import (
    AcknowledgeTelegramTapsUseCase,
)
from app.use_cases.channels.connection.connect_channel_use_case import (
    ConnectChannelUseCase,
)
from app.use_cases.channels.create_telegram_link_use_case import (
    CreateTelegramLinkUseCase,
)
from app.use_cases.channels.disable_channel_use_case import DisableChannelUseCase
from app.use_cases.channels.handle_platform_bot_update_use_case import (
    HandlePlatformBotUpdateUseCase,
)
from app.use_cases.channels.list_channels_use_case import ListChannelsUseCase
from app.use_cases.channels.receive_meta_webhook_use_case import (
    ReceiveMetaWebhookUseCase,
)
from app.use_cases.channels.receive_telegram_webhook_use_case import (
    ReceiveTelegramWebhookUseCase,
)
from app.use_cases.channels.set_whatsapp_staff_template_use_case import (
    SetWhatsAppStaffTemplateUseCase,
)
from app.use_cases.voice.audit_call_replies_use_case import (
    AuditCallRepliesUseCase,
)
from app.use_cases.voice.call_message_outbox import CallMessageOutbox
from app.use_cases.voice.finished_call.record_finished_call_use_case import (
    RecordFinishedCallUseCase,
)
from app.use_cases.voice.send_call_confirmation_use_case import (
    SendCallConfirmationUseCase,
)
from app.use_cases.voice.send_call_links_use_case import SendCallLinksUseCase
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.analytics.recording_product_events import RecordingProductEvents
from tests.brain.fake_contact_tools import FakeHandoff
from tests.channels.channels_fakes import RecordingVoiceAgentRemoval
from tests.channels.channels_infrastructure import ChannelsInfrastructure
from tests.foundation.access_support import ACCESS_SETTINGS, AllowStepUp
from tests.foundation.support_access_builders import build_authorize_business_access


class ChannelsUseCases(ChannelsInfrastructure):
    """Webhooks, channel settings, platform bot and finished-call use cases."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        super().__init__(settings)
        self.product_events = RecordingProductEvents()
        self.authorize_business_access = build_authorize_business_access(
            self.business_repo,
            self.user_repo,
            self.audit_log_repo,
            self.wall_clock,
            session_assurance=SessionAssuranceContext(),
            app_settings=ACCESS_SETTINGS,
        )
        # Messages to a caller after the call go through the outbox.
        self.call_messages = CallMessageOutbox(
            channel_repo=self.channel_repo,
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
            outbound_message_repo=self.outbound_message_repo,
            job_queue=self.job_queue,
            unit_of_work=None,
            wall_clock=self.wall_clock,
        )
        self.receive_telegram_webhook = ReceiveTelegramWebhookUseCase(
            self.channel_repo, self.secret_cipher, self.telegram_adapter
        )
        self.acknowledge_telegram_taps = AcknowledgeTelegramTapsUseCase(
            self.channel_repo, self.secret_cipher, self.telegram_adapter
        )
        self.receive_meta_webhook = ReceiveMetaWebhookUseCase(
            self.channel_repo,
            self.whatsapp_adapter,
            self.messenger_adapter,
            self.instagram_adapter,
        )
        self.connect_channel = ConnectChannelUseCase(
            self.authorize_business_access,
            self.channel_repo,
            self.secret_cipher,
            self.telegram_client,
            self.meta_client,
            self.phone_number_parser,
            self.audit_log_repo,
            self.settings,
            self.wall_clock,
            StorageScopeContext(),
            product_events=self.product_events,
            step_up=AllowStepUp(),
        )
        self.voice_agent_removals: list[BusinessId] = []
        self.disable_channel = DisableChannelUseCase(
            self.authorize_business_access,
            self.channel_repo,
            self.secret_cipher,
            self.telegram_client,
            self.audit_log_repo,
            self.wall_clock,
            RecordingVoiceAgentRemoval(self.voice_agent_removals),
        )
        self.set_whatsapp_staff_template = SetWhatsAppStaffTemplateUseCase(
            self.authorize_business_access,
            self.channel_repo,
            self.audit_log_repo,
            self.wall_clock,
        )
        self.list_channels = ListChannelsUseCase(
            self.authorize_business_access, self.channel_repo
        )
        self.create_telegram_link = CreateTelegramLinkUseCase(
            self.authorize_business_access,
            self.link_repo,
            self.language_registry,
            self.telegram_client,
            self.settings,
            self.wall_clock,
        )
        self.handle_platform_bot_update = HandlePlatformBotUpdateUseCase(
            self.link_repo,
            self.business_repo,
            self.audit_log_repo,
            self.telegram_client,
            self.text_resolver,
            self.settings,
            self.wall_clock,
        )
        self.record_finished_call = RecordFinishedCallUseCase(
            self.channel_repo,
            self.business_repo,
            self.assistant_version_repo,
            self.conversation_repo,
            self.call_repo,
            self.booking_repo,
            self.lead_repo,
            self.handoff_repo,
            self.usage_event_repo,
            self.audit_log_repo,
            self.phone_number_parser,
            self.wall_clock,
        )
        self.send_call_confirmation = SendCallConfirmationUseCase(
            self.business_repo,
            self.booking_repo,
            self.contact_repo,
            self.call_messages,
            self.text_resolver,
        )
        self.send_call_links = SendCallLinksUseCase(
            self.business_repo,
            self.profile_repo,
            self.contact_repo,
            self.message_repo,
            self.call_messages,
            self.text_resolver,
        )
        # The after-call check of what the assistant said; its handoffs are
        # stored by a fake that records them.
        self.call_handoff = FakeHandoff(
            self.handoff_repo, self.conversation_repo, self.wall_clock
        )
        self.audit_call_replies = AuditCallRepliesUseCase(
            self.business_repo,
            self.call_repo,
            self.conversation_repo,
            self.assistant_version_repo,
            self.message_repo,
            self.booking_repo,
            self.call_handoff,
            self.wall_clock,
        )
