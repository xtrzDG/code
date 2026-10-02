"""HTTP clients of messaging and voice platforms used by the channels module."""

from typing import Protocol

from app.contracts.client_contract import ClientContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.call_recordings import RecordingAudio
from app.schemas.dto.channels.provider_profiles import (
    MetaPageProfile,
    TelegramBotProfile,
    WhatsAppPhoneNumberProfile,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.constrained_strings import (
    ChannelWebhookUrl,
    MetaObjectId,
    TelegramWebhookSecret,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import (
    ChannelSecret,
    OutboundMessagePart,
    VoicePlatformToolId,
)
from app.schemas.typings.conversations.strings import ChannelUserId, ProviderCallId
from app.schemas.typings.platform.strings import PlatformSecret

# Raw JSON object exchanged with a provider (the external boundary).
type JsonObject = dict[str, object]
# A business's bot or page token, or a platform-wide token.
type ProviderToken = ChannelSecret | PlatformSecret


class TelegramBotApiClientContract(ClientContract, Protocol):
    """Telegram Bot API; every call names the bot by its token."""

    def get_me(self, bot_token: ProviderToken) -> TelegramBotProfile:
        """Raises ValidationFailedError for a rejected token."""
        raise NotImplementedError

    def set_webhook(
        self,
        bot_token: ProviderToken,
        url: ChannelWebhookUrl,
        secret_token: TelegramWebhookSecret,
    ) -> None:
        raise NotImplementedError

    def delete_webhook(self, bot_token: ProviderToken) -> None:
        raise NotImplementedError

    def send_message(
        self,
        bot_token: ProviderToken,
        chat_id: ChannelUserId,
        text: OutboundMessagePart,
    ) -> None:
        """Send at most 4096 characters. Raises ExternalServiceError."""
        raise NotImplementedError


class MetaGraphApiClientContract(ClientContract, Protocol):
    """Meta Graph API: WhatsApp Cloud API, Messenger and Instagram messaging."""

    def get_whatsapp_phone_number(
        self,
        access_token: ProviderToken,
        phone_number_id: MetaObjectId,
    ) -> WhatsAppPhoneNumberProfile:
        """Raises ValidationFailedError when the number is not accessible."""
        raise NotImplementedError

    def subscribe_whatsapp_business_account(
        self,
        access_token: ProviderToken,
        business_account_id: MetaObjectId,
    ) -> None:
        """Subscribe the platform app to the account's message webhooks."""
        raise NotImplementedError

    def get_page(
        self,
        access_token: ProviderToken,
        page_id: MetaObjectId,
    ) -> MetaPageProfile:
        """Raises ValidationFailedError for a rejected token or unknown page."""
        raise NotImplementedError

    def subscribe_page(
        self,
        access_token: ProviderToken,
        page_id: MetaObjectId,
    ) -> None:
        """Subscribe the platform app to the page's message webhooks."""
        raise NotImplementedError

    def send_whatsapp_text(
        self,
        access_token: ProviderToken,
        phone_number_id: MetaObjectId,
        recipient: ChannelUserId,
        text: OutboundMessagePart,
    ) -> None:
        """Free-form text (at most 4096 characters, 24-hour window)."""
        raise NotImplementedError

    def send_whatsapp_template(
        self,
        access_token: ProviderToken,
        phone_number_id: MetaObjectId,
        recipient: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[OutboundMessagePart],
    ) -> None:
        raise NotImplementedError

    def send_page_message(
        self,
        access_token: ProviderToken,
        recipient: ChannelUserId,
        text: OutboundMessagePart,
    ) -> None:
        """Messenger or Instagram message through the page token's Send API."""
        raise NotImplementedError


class ElevenLabsApiClientContract(ClientContract, Protocol):
    """ElevenLabs Agents platform API."""

    def create_agent(self, agent_config: JsonObject) -> VoiceAgentId:
        raise NotImplementedError

    def get_agent_tool_ids(
        self,
        agent_id: VoiceAgentId,
    ) -> list[VoicePlatformToolId] | None:
        """Tool ids attached to the agent; None when the agent is gone."""
        raise NotImplementedError

    def update_agent(self, agent_id: VoiceAgentId, agent_config: JsonObject) -> None:
        raise NotImplementedError

    def delete_agent(self, agent_id: VoiceAgentId) -> None:
        """Delete an agent; a missing one is not an error."""
        raise NotImplementedError

    def create_tool(self, tool_config: JsonObject) -> VoicePlatformToolId:
        raise NotImplementedError

    def get_tool_name(self, tool_id: VoicePlatformToolId) -> AssistantToolName | None:
        """
        Name of one of the assistant's tools; None when the tool is gone or
        is not an assistant tool.
        """
        raise NotImplementedError

    def update_tool(
        self, tool_id: VoicePlatformToolId, tool_config: JsonObject
    ) -> None:
        raise NotImplementedError

    def delete_tool(self, tool_id: VoicePlatformToolId) -> None:
        raise NotImplementedError

    def get_conversation_audio(
        self,
        conversation_id: ProviderCallId,
    ) -> RecordingAudio | None:
        """The audio recording of a call; None when the platform has none."""
        raise NotImplementedError

    def delete_conversation(self, conversation_id: ProviderCallId) -> None:
        """Delete a call's recording and transcript; a missing one is not an error."""
        raise NotImplementedError
