import logging

from app.contracts.channel_clients import (
    MetaGraphApiClientContract,
    MetaTypingClientContract,
)
from app.contracts.channels import (
    ChannelAdapterContract,
    WhatsAppTemplateAdapterContract,
)
from app.contracts.localization_utilities import (
    LocalizedTextResolverContract,
    PhoneNumberParserContract,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.reply_choices import ReplyChoices
from app.schemas.dto.channels.channel_webhooks import (
    ChannelDeliveryTarget,
    ChannelInboundMessage,
    ChannelSendReceipt,
    ChannelWebhookPayload,
)
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
)
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
    OutboundMessagePart,
    ProviderMessageId,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.choice_delivery import send_with_choices, split_reply
from app.utilities.channels.choice_payloads import (
    whatsapp_body_limit,
    whatsapp_interactive,
)
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_object,
    read_objects,
    read_text,
)
from app.utilities.channels.skipped_webhook_parts import log_skipped_parts
from app.utilities.channels.webhook_signatures import is_valid_sha256_signature
from app.utilities.channels.whatsapp_inbound_messages import read_change_messages
from app.utilities.channels.whatsapp_webhook_parts import (
    ROUTINE_KINDS,
    other_field_kind,
    status_kinds,
)
from app.utilities.conversations.assistant_texts.choice_texts import (
    CHOICE_LIST_BUTTON,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
WEBHOOK_OBJECT: str = "whatsapp_business_account"
MESSAGES_FIELD: str = "messages"
# Limit of a text message body in the Cloud API.
WHATSAPP_MESSAGE_LIMIT: int = 4096
# Limit of one template body parameter.
WHATSAPP_TEMPLATE_PARAMETER_LIMIT: int = 1024
TRUNCATION_MARK: str = "…"
PLATFORM: str = "WhatsApp"


class WhatsAppChannelAdapter(ChannelAdapterContract, WhatsAppTemplateAdapterContract):
    """
    WhatsApp Cloud API, one platform app for every business.

    Webhooks are signed with the app secret (X-Hub-Signature-256); the
    business is found by the phone number id in `metadata`. Messages are
    sent with the platform system user token.

    The 24-hour customer service window: free-form replies are allowed only
    within 24 hours of the customer's last message, which covers every chat
    answer. Booking confirmations and reminders sent later, and staff
    notifications, must use templates approved by Meta (`send_template`).
    """

    def __init__(
        self,
        meta_client: MetaGraphApiClientContract,
        phone_number_parser: PhoneNumberParserContract,
        app_settings: AppSettings,
        typing_client: MetaTypingClientContract | None = None,
        text_resolver: LocalizedTextResolverContract | None = None,
    ) -> None:
        self._text_resolver: LocalizedTextResolverContract | None = text_resolver
        self._meta_client: MetaGraphApiClientContract = meta_client
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._app_settings: AppSettings = app_settings
        self._typing_client: MetaTypingClientContract | None = typing_client

    def verify_signature(
        self,
        payload: ChannelWebhookPayload,
        channel_secret: ChannelSecret | None,
    ) -> None:
        del channel_secret
        app_secret: PlatformSecret | None = self._app_settings.meta_app_secret
        if app_secret is None or not is_valid_sha256_signature(
            str(app_secret),
            payload.body,
            payload.signature_header,
        ):
            raise AuthenticationRequiredError(
                "The Meta webhook signature is missing or wrong."
            )

    def parse_webhook(
        self,
        payload: ChannelWebhookPayload,
    ) -> list[ChannelInboundMessage]:
        root: JsonObject | None = parse_json_object(payload.body)
        if root is None or read_text(root, "object") != WEBHOOK_OBJECT:
            return []

        messages: list[ChannelInboundMessage] = []
        skipped: list[str] = []
        for entry in read_objects(root, "entry"):
            for change in read_objects(entry, "changes"):
                value: JsonObject | None = read_object(change, "value")
                if read_text(change, "field") != MESSAGES_FIELD or value is None:
                    skipped.append(other_field_kind(change))
                    continue

                skipped.extend(status_kinds(value))
                messages.extend(
                    read_change_messages(value, skipped, self._phone_number_parser)
                )

        log_skipped_parts(LOGGER, PLATFORM, skipped, ROUTINE_KINDS)
        return messages

    def split(
        self, text: MessageText, choices: ReplyChoices | None = None
    ) -> list[MessageText]:
        return [
            MessageText(part)
            for part in split_reply(
                str(text),
                WHATSAPP_MESSAGE_LIMIT,
                choices,
                None if choices is None else whatsapp_body_limit(choices),
            )
        ]

    def send(
        self,
        target: ChannelDeliveryTarget,
        text: MessageText,
        choices: ReplyChoices | None = None,
    ) -> ChannelSendReceipt:
        """Options go as reply buttons (up to three) or a list (up to ten)."""

        parts: list[MessageText] = self.split(text, choices)
        provider_message_id: ProviderMessageId | None = None
        for index, part in enumerate(parts):
            provider_message_id = (
                self._send_with_choices(target, str(part), choices)
                if choices is not None and index == len(parts) - 1
                else self._send_text(target, str(part))
            )

        return ChannelSendReceipt(
            delivered=DeliveredMessageCount(len(parts)),
            provider_message_id=provider_message_id,
        )

    def _send_text(
        self, target: ChannelDeliveryTarget, part: str
    ) -> ProviderMessageId | None:
        return self._meta_client.send_whatsapp_text(
            self._require_token(),
            require_phone_number_id(target.account_id),
            target.channel_user_id,
            OutboundMessagePart(part),
        )

    def _send_with_choices(
        self, target: ChannelDeliveryTarget, part: str, choices: ReplyChoices
    ) -> ProviderMessageId | None:
        def send_buttons(body: str) -> ProviderMessageId | None:
            return self._meta_client.send_whatsapp_interactive(
                self._require_token(),
                require_phone_number_id(target.account_id),
                target.channel_user_id,
                whatsapp_interactive(body, choices, self._list_button(choices)),
            )

        return send_with_choices(
            PLATFORM,
            part,
            choices,
            send_buttons,
            lambda body: self._send_text(target, body),
        )

    def _list_button(self, choices: ReplyChoices) -> str:
        """The list's button label in the options' language."""

        if self._text_resolver is None or choices.language is None:
            return str(CHOICE_LIST_BUTTON.values[LanguageTag("en")])

        return str(self._text_resolver.resolve(CHOICE_LIST_BUTTON, choices.language))

    def signal_typing(
        self,
        target: ChannelDeliveryTarget,
        replying_to: ProviderMessageId | None,
    ) -> None:
        """The typing indicator goes with the read receipt of the message."""

        if self._typing_client is None or replying_to is None:
            return

        self._typing_client.show_whatsapp_typing(
            self._require_token(),
            require_phone_number_id(target.account_id),
            replying_to,
        )

    def send_template(
        self,
        phone_number_id: MetaObjectId,
        recipient: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[MessageText],
    ) -> ProviderMessageId | None:
        return self._meta_client.send_whatsapp_template(
            self._require_token(),
            phone_number_id,
            recipient,
            template_name,
            language_code,
            [
                OutboundMessagePart(
                    truncate_text(str(parameter), WHATSAPP_TEMPLATE_PARAMETER_LIMIT)
                )
                for parameter in body_parameters
            ],
        )

    def _require_token(self) -> PlatformSecret:
        access_token: PlatformSecret | None = (
            self._app_settings.whatsapp_system_user_token
        )
        if access_token is None:
            raise ExternalServiceError(
                "WhatsApp is not configured: WHATSAPP_SYSTEM_USER_TOKEN is missing."
            )

        return access_token


def require_phone_number_id(account_id: ChannelExternalId | None) -> MetaObjectId:
    try:
        return MetaObjectId(str(account_id))
    except ValueError as error:
        raise ExternalServiceError(
            "The WhatsApp number of this business is not connected."
        ) from error


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text

    return text[: limit - len(TRUNCATION_MARK)].rstrip() + TRUNCATION_MARK
