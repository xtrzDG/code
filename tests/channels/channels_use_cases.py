"""The channels testbed's use cases and facilitators, wired over its infrastructure."""

from app.facilitators.channels.channel_message_sender_facilitator import (
    ChannelMessageSenderFacilitator,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.channels.connection.connect_channel_use_case import (
    ConnectChannelUseCase,
)
from app.use_cases.channels.create_telegram_link_use_case import (
    CreateTelegramLinkUseCase,
)
from app.use_cases.channels.deliver_channel_reply_use_case import (
    DeliverChannelReplyUseCase,
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
from app.use_cases.voice.finished_call.record_finished_call_use_case import (
    RecordFinishedCallUseCase,
)
from app.use_cases.voice.send_call_confirmation_use_case import (
    SendCallConfirmationUseCase,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.brain.fake_contact_tools import FakeHandoff
from tests.channels.channels_fakes import RecordingVoiceAgentRemoval
from tests.channels.channels_infrastructure import ChannelsInfrastructure


class ChannelsUseCases(ChannelsInfrastructure):
    """Webhooks, channel settings, platform bot and finished-call use cases."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        super().__init__(settings)
        self.authorize_business_access = AuthorizeBusinessAccessUseCase(
            self.business_repo, self.user_repo, self.audit_log_repo, self.wall_clock
        )
        self.channel_message_sender = ChannelMessageSenderFacilitator(
            self.channel_repo,
            self.secret_cipher,
            self.telegram_adapter,
            self.whatsapp_adapter,
            self.messenger_adapter,
            self.instagram_adapter,
            self.whatsapp_adapter,
            self.usage_event_repo,
            self.wall_clock,
        )
        self.deliver_reply = DeliverChannelReplyUseCase(
            self.telegram_adapter,
            self.whatsapp_adapter,
            self.messenger_adapter,
            self.instagram_adapter,
            self.usage_event_repo,
            self.channel_repo,
            self.wall_clock,
        )
        self.receive_telegram_webhook = ReceiveTelegramWebhookUseCase(
            self.channel_repo,
            self.secret_cipher,
            self.telegram_adapter,
            self.receipt_repo,
            self.wall_clock,
        )
        self.receive_meta_webhook = ReceiveMetaWebhookUseCase(
            self.channel_repo,
            self.secret_cipher,
            self.whatsapp_adapter,
            self.messenger_adapter,
            self.instagram_adapter,
            self.receipt_repo,
            self.wall_clock,
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
            self.channel_repo,
            self.channel_message_sender,
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
