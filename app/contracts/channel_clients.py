"""HTTP clients of messaging and voice platforms used by the channels module."""

from typing import Protocol

from app.contracts.client_contract import ClientContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.call_recordings import RecordingAudio
from app.schemas.dto.channels.provider_profiles import (
    MetaPageProfile,
    TelegramBotProfile,
    TelegramWebhookInfo,
    WhatsAppPhoneNumberProfile,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.constrained_strings import (
    ChannelWebhookUrl,
    MetaObjectId,
    TelegramBotUserId,
    TelegramWebhookSecret,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import (
    ChannelSecret,
    OutboundMessagePart,
    ProviderMessageId,
    TelegramCallbackQueryId,
    VoicePlatformToolId,
)
from app.schemas.typings.conversations.strings import ChannelUserId, ProviderCallId
from app.schemas.typings.media.strings import ProviderMediaId
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

    def get_profile_photo_file_id(
        self, bot_token: ProviderToken, bot_user_id: TelegramBotUserId
    ) -> ProviderMediaId | None:
        """
        `getUserProfilePhotos` of the bot: the file of its current photo in
        a small size (None: no photo). Errors as `send_message`.
        """
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
        reply_markup: JsonObject | None = None,
    ) -> ProviderMessageId | None:
        """
        Send at most 4096 characters, with an inline keyboard when given;
        the sent message's id ("<chat id>:<message id>"). Raises
        ProviderRateLimitedError (429), ChannelCredentialRejectedError (the
        token), ProviderRejectedMessageError (another 4xx: blocked bot,
        unknown chat, a bad keyboard), ExternalServiceError.
        """
        raise NotImplementedError

    def answer_callback_query(
        self, bot_token: ProviderToken, callback_query_id: TelegramCallbackQueryId
    ) -> None:
        """
        Tell Telegram a button tap was received (the button stops showing
        progress). Errors as `send_message`.
        """
        raise NotImplementedError

    def edit_message_text(
        self,
        bot_token: ProviderToken,
        message_id: ProviderMessageId,
        text: OutboundMessagePart,
    ) -> None:
        """
        Replace the text of a sent message ("<chat id>:<message id>") and
        remove its inline keyboard. Errors as `send_message`.
        """
        raise NotImplementedError

    def get_webhook_info(self, bot_token: ProviderToken) -> TelegramWebhookInfo:
        """Where the bot's webhook points and whether it gets button taps."""
        raise NotImplementedError

    def send_typing_action(
        self, bot_token: ProviderToken, chat_id: ChannelUserId
    ) -> None:
        """
        `sendChatAction` "typing": the chat shows the bot typing for about
        5 seconds (or until it sends a message). Errors as `send_message`.
        """
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
    ) -> ProviderMessageId | None:
        """
        Free-form text (at most 4096 characters, 24-hour window); the
        "wamid..." of the sent message. Errors as `send_page_message`.
        """
        raise NotImplementedError

    def send_whatsapp_template(
        self,
        access_token: ProviderToken,
        phone_number_id: MetaObjectId,
        recipient: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[OutboundMessagePart],
    ) -> ProviderMessageId | None:
        """The "wamid..." of the sent template message."""
        raise NotImplementedError

    def send_whatsapp_interactive(
        self,
        access_token: ProviderToken,
        phone_number_id: MetaObjectId,
        recipient: ChannelUserId,
        interactive: JsonObject,
    ) -> ProviderMessageId | None:
        """
        An interactive message (reply buttons or a list) within the 24-hour
        window; the "wamid..." of the sent message. Errors as
        `send_page_message`.
        """
        raise NotImplementedError

    def send_page_message(
        self,
        access_token: ProviderToken,
        recipient: ChannelUserId,
        text: OutboundMessagePart,
        quick_replies: list[JsonObject] | None = None,
    ) -> ProviderMessageId | None:
        """
        Messenger or Instagram message through the page token's Send API,
        with quick replies under it when given; the "mid..." of the sent
        message. Raises ProviderRateLimitedError
        (429, throttling codes), ChannelCredentialRejectedError (the token),
        WhatsAppTemplateRejectedError, ProviderRejectedMessageError (another
        4xx), ExternalServiceError (5xx, network).
        """
        raise NotImplementedError


class MetaTypingClientContract(ClientContract, Protocol):
    """The "typing…" signals of the WhatsApp Cloud API and the Send API."""

    def show_whatsapp_typing(
        self,
        access_token: ProviderToken,
        phone_number_id: MetaObjectId,
        message_id: ProviderMessageId,
    ) -> None:
        """
        Mark the customer's message read with a typing indicator (shown up
        to 25 seconds, or until the reply). Errors as `send_page_message`.
        """
        raise NotImplementedError

    def show_page_typing(
        self,
        access_token: ProviderToken,
        recipient: ChannelUserId,
    ) -> None:
        """
        Messenger or Instagram `sender_action` "typing_on" (shown up to 20
        seconds, or until the reply). Errors as `send_page_message`.
        """
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
