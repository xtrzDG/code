from app.contracts.channel_clients import MetaGraphApiClientContract
from app.contracts.channels import (
    ChannelAdapterContract,
    WhatsAppTemplateAdapterContract,
)
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.message_media import InboundAttachment
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
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.attachment_reading import has_content
from app.utilities.channels.channel_phone_numbers import (
    parse_messaging_phone_number,
)
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_identifier,
    read_object,
    read_objects,
    read_text,
)
from app.utilities.channels.message_chunks import split_message_text
from app.utilities.channels.webhook_signatures import is_valid_sha256_signature
from app.utilities.channels.whatsapp_attachments import read_whatsapp_attachments

WEBHOOK_OBJECT: str = "whatsapp_business_account"
MESSAGES_FIELD: str = "messages"
# Limit of a text message body in the Cloud API.
WHATSAPP_MESSAGE_LIMIT: int = 4096
# Limit of one template body parameter.
WHATSAPP_TEMPLATE_PARAMETER_LIMIT: int = 1024
TRUNCATION_MARK: str = "…"
MAX_CONTACT_NAME_LENGTH: int = 128


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
    ) -> None:
        self._meta_client: MetaGraphApiClientContract = meta_client
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._app_settings: AppSettings = app_settings

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
        for entry in read_objects(root, "entry"):
            for change in read_objects(entry, "changes"):
                value: JsonObject | None = read_object(change, "value")
                if read_text(change, "field") != MESSAGES_FIELD or value is None:
                    continue

                messages.extend(self._read_change_messages(value))

        return messages

    def split(self, text: MessageText) -> list[MessageText]:
        return [
            MessageText(part)
            for part in split_message_text(str(text), WHATSAPP_MESSAGE_LIMIT)
        ]

    def send(
        self,
        target: ChannelDeliveryTarget,
        text: MessageText,
    ) -> ChannelSendReceipt:
        access_token: PlatformSecret = self._require_token()
        phone_number_id: MetaObjectId = require_phone_number_id(target.account_id)
        parts: list[MessageText] = self.split(text)
        provider_message_id: ProviderMessageId | None = None
        for part in parts:
            provider_message_id = self._meta_client.send_whatsapp_text(
                access_token,
                phone_number_id,
                target.channel_user_id,
                OutboundMessagePart(str(part)),
            )

        return ChannelSendReceipt(
            delivered=DeliveredMessageCount(len(parts)),
            provider_message_id=provider_message_id,
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

    def _read_change_messages(self, value: JsonObject) -> list[ChannelInboundMessage]:
        metadata: JsonObject = read_object(value, "metadata") or {}
        phone_number_id: str | None = read_identifier(metadata, "phone_number_id")
        if phone_number_id is None:
            return []

        profile_names: dict[str, str] = {}
        for contact in read_objects(value, "contacts"):
            wa_id: str | None = read_identifier(contact, "wa_id")
            profile: JsonObject = read_object(contact, "profile") or {}
            name: str | None = read_text(profile, "name")
            if wa_id is not None and name is not None:
                profile_names[wa_id] = name

        messages: list[ChannelInboundMessage] = []
        for message in read_objects(value, "messages"):
            sender: str | None = read_identifier(message, "from")
            text: str = read_message_text(message) or ""
            attachments: list[InboundAttachment] = read_whatsapp_attachments(message)
            if sender is None or not has_content(text, attachments):
                continue

            message_id: str | None = read_text(message, "id")
            contact_name: str | None = profile_names.get(sender)
            messages.append(
                ChannelInboundMessage(
                    channel=ChannelKind.WHATSAPP,
                    account_id=ChannelExternalId(phone_number_id),
                    channel_user_id=ChannelUserId(sender),
                    text=MessageText(text),
                    contact_name=(
                        None
                        if contact_name is None
                        else ContactName(contact_name[:MAX_CONTACT_NAME_LENGTH])
                    ),
                    contact_phone_number=parse_messaging_phone_number(
                        self._phone_number_parser,
                        sender,
                    ),
                    provider_message_id=(
                        None if message_id is None else ProviderMessageId(message_id)
                    ),
                    attachments=attachments,
                )
            )

        return messages


def read_message_text(message: JsonObject) -> str | None:
    """
    Text of a customer message: typed text, a tapped template button or an
    interactive reply. Media and places are attachments
    (`whatsapp_attachments`); reactions have neither.
    """

    message_type: str | None = read_text(message, "type")
    if message_type == "text":
        return read_text(read_object(message, "text") or {}, "body")

    if message_type == "button":
        return read_text(read_object(message, "button") or {}, "text")

    if message_type == "interactive":
        interactive: JsonObject = read_object(message, "interactive") or {}
        for reply_key in ("button_reply", "list_reply"):
            reply: JsonObject | None = read_object(interactive, reply_key)
            if reply is not None:
                return read_text(reply, "title")

    return None


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
