from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channel_events import PlatformBotCommandResult
from app.schemas.constants.channels import ChannelKind, ChannelStatus, WidgetPosition
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.localization import TextDirection
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.dto.staff_reply_templates import WhatsAppStaffTemplateView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.booleans import (
    HasChannelCredential,
    HasMoreWidgetMessages,
    IsWebChatEnabled,
)
from app.schemas.typings.channels.constrained_integers import WebhookMessageCount
from app.schemas.typings.channels.constrained_strings import (
    ChannelErrorSummary,
    ManagerLinkCode,
    MetaObjectId,
    TelegramBotUsername,
    TelegramDeepLink,
    WidgetAccentColor,
    WidgetDemoUrl,
    WidgetMessageText,
    WidgetScriptUrl,
    WidgetSessionKey,
)
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
    MetaPageName,
    MetaWebhookChallenge,
    MetaWebhookMode,
    PresentedWebhookSecret,
    ProviderMessageId,
    RawChannelSecretInput,
    WebhookSignatureHeader,
    WhatsAppDisplayPhoneNumber,
    WidgetContactNameInput,
    WidgetEmbedSnippet,
    WidgetGreetingText,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import IsConversationHandedOff
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.handoffs.strings import ManagerName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import (
    LanguageDisplayName,
    RawPhoneNumberInput,
)
from app.schemas.typings.users.prefixed_id import UserId

# --- Webhooks of messaging platforms ---------------------------------------


class ChannelWebhookPayload(ImmutableDTO):
    """
    One webhook delivery exactly as it arrived: the raw body bytes (signatures
    are computed over them) and the platform's authentication header
    (Meta X-Hub-Signature-256, Telegram X-Telegram-Bot-Api-Secret-Token).
    """

    body: bytes
    signature_header: WebhookSignatureHeader | None = None


class TelegramWebhookRequest(ImmutableDTO):
    """Webhook of one business's Telegram bot; the URL names the channel."""

    channel_id: ChannelId
    payload: ChannelWebhookPayload


class MetaWebhookRequest(ImmutableDTO):
    """Webhook of the Meta app: WhatsApp, Messenger and Instagram in one."""

    payload: ChannelWebhookPayload


class MetaWebhookVerificationRequest(ImmutableDTO):
    """GET verification of the Meta webhook (hub.mode, hub.verify_token, ...)."""

    mode: MetaWebhookMode | None = None
    verify_token: PresentedWebhookSecret | None = Field(default=None, repr=False)
    challenge: MetaWebhookChallenge | None = None


class ChannelInboundMessage(ImmutableDTO):
    """
    A customer message as a channel adapter reads it (the concept's
    InboundMessage before the business is resolved).

    `account_id` is the business account inside the channel (WhatsApp phone
    number id, Facebook page id, Instagram account id); it is None when the
    webhook address already names the channel (Telegram).
    """

    channel: ChannelKind
    account_id: ChannelExternalId | None = None
    channel_user_id: ChannelUserId
    text: MessageText
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    provider_message_id: ProviderMessageId | None = None


class ChannelDeliveryTarget(ImmutableDTO):
    """
    Where a message to a customer goes: the business's account in a channel
    and the customer inside it.

    `credential` is the decrypted bot or page token (None for WhatsApp, which
    uses the platform token). It is excluded from the representation so it
    never reaches logs.
    """

    channel: ChannelKind
    account_id: ChannelExternalId | None = None
    channel_user_id: ChannelUserId
    credential: ChannelSecret | None = Field(default=None, repr=False)


class ChannelInboundDelivery(ImmutableDTO):
    """A customer message ready for the assistant and the way back to them."""

    message: InboundMessage
    target: ChannelDeliveryTarget


class ChannelReplyDelivery(ImmutableDTO):
    """An assistant reply to send to a customer in their channel."""

    business_id: BusinessId
    conversation_id: ConversationId | None = None
    target: ChannelDeliveryTarget
    text: MessageText


class ChannelWebhookOutcome(ImmutableDTO):
    """
    What happened to the customer messages of one webhook delivery.

    `silenced` counts messages the assistant did not answer because staff
    took over the conversation; `failed` counts messages that could not be
    answered or delivered (the delivery is still acknowledged so the
    platform does not repeat messages that were answered).
    """

    received: WebhookMessageCount = WebhookMessageCount(0)
    answered: WebhookMessageCount = WebhookMessageCount(0)
    silenced: WebhookMessageCount = WebhookMessageCount(0)
    failed: WebhookMessageCount = WebhookMessageCount(0)


# --- Provider account profiles ---------------------------------------------


class TelegramBotProfile(ImmutableDTO):
    """A Telegram bot as getMe describes it."""

    username: TelegramBotUsername


class MetaPageProfile(ImmutableDTO):
    """A Facebook page and its linked Instagram professional account."""

    page_id: MetaObjectId
    name: MetaPageName | None = None
    instagram_account_id: MetaObjectId | None = None


class WhatsAppPhoneNumberProfile(ImmutableDTO):
    """A WhatsApp Cloud API business phone number."""

    phone_number_id: MetaObjectId
    display_phone_number: WhatsAppDisplayPhoneNumber | None = None


# --- Cabinet: connected channels -------------------------------------------


class ConnectChannelRequest(ImmutableDTO):
    """
    HTTP body that connects a channel; the fields needed depend on the kind.

    - telegram: `bot_token` from @BotFather.
    - whatsapp: `phone_number_id` from Embedded Signup and, to subscribe the
      app to its webhooks, `whatsapp_business_account_id`.
    - messenger, instagram: `page_id` and `page_access_token` (Facebook
      Login); Instagram uses the professional account linked to the page.
    - phone: `phone_number` of the assistant line (any country; national
      formats are read in `country_hint` or the business country).
    - web_chat: nothing to switch it on; optionally `widget_color` (hex brand
      colour) and `widget_position` (left or right) for the widget. Fields
      left out keep their saved values.
    """

    bot_token: RawChannelSecretInput | None = Field(default=None, repr=False)
    phone_number_id: MetaObjectId | None = None
    whatsapp_business_account_id: MetaObjectId | None = None
    page_id: MetaObjectId | None = None
    page_access_token: RawChannelSecretInput | None = Field(default=None, repr=False)
    phone_number: RawPhoneNumberInput | None = None
    country_hint: CountryCode | None = None
    widget_color: WidgetAccentColor | None = None
    widget_position: WidgetPosition | None = None


class ConnectChannelCommand(ImmutableDTO):
    """Owner connects (or reconnects) one channel of a business."""

    user_id: UserId
    business_id: BusinessId
    channel: ChannelKind
    request: ConnectChannelRequest
    client_ip_address: ClientIpAddress | None = None


class DisableChannelCommand(ImmutableDTO):
    """Owner switches a channel off; its credential is erased."""

    user_id: UserId
    business_id: BusinessId
    channel: ChannelKind
    client_ip_address: ClientIpAddress | None = None


class ChannelListQuery(ImmutableDTO):
    """List the channels of a business for a signed-in member."""

    user_id: UserId
    business_id: BusinessId


class ChannelView(ImmutableDTO):
    """
    A channel as the cabinet shows it; credentials are never returned.

    `account_id` is the public account inside the channel: bot username,
    WhatsApp phone number id, page id, Instagram account id, or the E.164
    number of the assistant line. With status ERROR, `last_error` is the
    platform's short reason (no secrets) and `last_error_at` its time. The
    website chat also reports its saved colour and launcher corner (None:
    the widget's defaults). WhatsApp reports the template staff replies use
    once the 24-hour window has closed (None: no template, such replies are
    refused).
    """

    id: ChannelId
    business_id: BusinessId
    channel: ChannelKind
    status: ChannelStatus
    account_id: ChannelExternalId | None = None
    has_credential: HasChannelCredential
    updated_at: Microseconds
    last_error: ChannelErrorSummary | None = None
    last_error_at: Microseconds | None = None
    widget_color: WidgetAccentColor | None = None
    widget_position: WidgetPosition | None = None
    staff_reply_template: WhatsAppStaffTemplateView | None = None


# --- Website chat widget ---------------------------------------------------


class WidgetLanguageView(ImmutableDTO):
    """A customer language of the widget with its writing direction."""

    tag: LanguageTag
    native_name: LanguageDisplayName
    direction: TextDirection


class WidgetGreetingView(ImmutableDTO):
    """The widget's first message in one customer language."""

    language: LanguageTag
    text: WidgetGreetingText
    direction: TextDirection


class WidgetConfigView(ImmutableDTO):
    """
    Public configuration the widget script loads before it shows itself.

    `business_name` is the name visitors see in the widget header.
    `greetings` holds the first message in the languages the live assistant
    answers in (the business languages before anything is published) where
    a text exists; the widget uses its own text for the others. `accent_color`
    and `position` are the owner's choices (None: the widget's defaults); the
    embed tag's data-color and data-position still win.
    """

    business_id: BusinessId
    business_name: BusinessName
    is_enabled: IsWebChatEnabled
    default_language: LanguageTag
    languages: list[WidgetLanguageView]
    greetings: list[WidgetGreetingView]
    accent_color: WidgetAccentColor | None = None
    position: WidgetPosition | None = None


class WidgetMessageRequest(ImmutableDTO):
    """HTTP body of a visitor message typed into the widget."""

    session_key: WidgetSessionKey
    text: WidgetMessageText
    contact_name: WidgetContactNameInput | None = None


class WidgetMessageCommand(ImmutableDTO):
    """A visitor message for one business's widget."""

    business_id: BusinessId
    request: WidgetMessageRequest


class WidgetReplyView(ImmutableDTO):
    """
    The assistant's answer in the widget.

    `text` is None while staff handle the conversation; `direction` tells the
    widget how to lay the answer out (right-to-left for Hebrew, Arabic, ...).
    `message_id` is the stored answer (None without one); `cursor` is the
    visitor's message, so polling GET .../messages?after=<cursor> returns
    the answer again (skip it by id) and every staff message written since.
    """

    conversation_id: ConversationId
    text: MessageText | None
    language: LanguageTag
    direction: TextDirection
    is_handed_off: IsConversationHandedOff
    message_id: MessageId | None = None
    cursor: MessageId | None = None


class WidgetReplyInput(ImmutableDTO):
    """The assistant's answer to a widget visitor of one business."""

    business_id: BusinessId
    reply: AssistantReply


class WidgetMessagesQuery(ImmutableDTO):
    """
    A widget polls for new answers of its visitor's conversations: the
    assistant's and staff's messages after the message `after`. Without
    `after` nothing is returned but the current position (a widget that has
    shown everything starts from there).
    """

    business_id: BusinessId
    session_key: WidgetSessionKey
    after: MessageId | None = None
    client_ip_address: ClientIpAddress | None = None


class WidgetMessageView(ImmutableDTO):
    """An assistant or staff message as the widget shows it."""

    id: MessageId
    author: MessageAuthor
    text: MessageText
    language: LanguageTag | None = None
    direction: TextDirection
    created_at: Microseconds


class WidgetMessagesView(ImmutableDTO):
    """
    New assistant and staff messages, oldest first (at most a page; poll
    again with `cursor` while `has_more`). `cursor` is the position to poll
    after next time (None while the visitor has no conversation);
    `is_handed_off` tells whether staff currently handle the conversation.
    """

    items: list[WidgetMessageView]
    cursor: MessageId | None = None
    has_more: HasMoreWidgetMessages = False
    is_handed_off: IsConversationHandedOff = False


class WidgetSnippetQuery(ImmutableDTO):
    """Ask for the embed code of a business's widget."""

    user_id: UserId
    business_id: BusinessId


class WidgetSnippetView(ImmutableDTO):
    """
    Embed code the owner pastes into the website, and the page that shows
    the widget as visitors see it (it accepts `color`, `position` and
    `language` to preview unsaved choices).
    """

    business_id: BusinessId
    script_url: WidgetScriptUrl
    snippet: WidgetEmbedSnippet
    demo_url: WidgetDemoUrl


# --- Staff notifications through the platform Telegram bot ----------------


class TelegramLinkRequest(ImmutableDTO):
    """
    HTTP body of a staff Telegram link; without `language` the owner's
    language is used for the staff member's notifications.
    """

    name: ManagerName
    language: LanguageTag | None = None


class CreateTelegramLinkCommand(ImmutableDTO):
    """Owner creates a one-time code that links a staff member's Telegram."""

    user_id: UserId
    business_id: BusinessId
    request: TelegramLinkRequest
    client_ip_address: ClientIpAddress | None = None


class TelegramLinkView(ImmutableDTO):
    """
    One-time link code. The staff member opens `deep_link` (or sends
    "/start <code>" to `bot_username`) before `expires_at`.
    """

    business_id: BusinessId
    code: ManagerLinkCode
    deep_link: TelegramDeepLink | None = None
    bot_username: TelegramBotUsername | None = None
    expires_at: Microseconds


class PlatformBotWebhookRequest(ImmutableDTO):
    """Webhook of the platform Telegram bot that notifies staff."""

    payload: ChannelWebhookPayload


class PlatformBotWebhookSetup(ImmutableDTO):
    """Register the platform bot's webhook with Telegram (deployment step)."""


class PlatformBotWebhookOutcome(ImmutableDTO):
    """How the platform bot handled the update."""

    result: PlatformBotCommandResult
