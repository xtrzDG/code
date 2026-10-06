"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ChannelErrorSummary(BaseConstrainedTypedString):
    """
    Short reason a connected channel stopped working, as the platform gave
    it, without tokens or customer data.

    Example:
        reason = ChannelErrorSummary("Telegram rejected the bot token (401).")
    """

    min_length = 1
    max_length = 300
    pattern = r"\S"


class ChannelWebhookUrl(BaseConstrainedTypedString):
    """
    Public HTTPS address a messaging platform delivers webhooks to.

    Example:
        url = ChannelWebhookUrl("https://api.example.com/v1/channels/meta/webhook")
    """

    min_length = 12
    max_length = 2048
    pattern = r"^https://[^\s/]+(/[^\s]*)?$"


class ManagerLinkCode(BaseConstrainedTypedString):
    """
    One-time code that links a staff member's Telegram chat to a business.

    Sent to the platform bot as "/start <code>"; upper-case Crockford base32.

    Example:
        code = ManagerLinkCode("7KQ2M9XH4D")
    """

    min_length = 10
    max_length = 10
    pattern = r"^[0-9A-HJKMNP-TV-Z]{10}$"


class MetaObjectId(BaseConstrainedTypedString):
    """
    Numeric id of a Meta Graph object: WhatsApp phone number or business
    account, Facebook page, Instagram professional account.

    Example:
        phone_number_id = MetaObjectId("106540352242922")
    """

    min_length = 1
    max_length = 32
    pattern = r"^[0-9]{1,32}$"


class PublicBaseUrl(BaseConstrainedTypedString):
    """
    Public HTTPS origin of this backend, used to register channel webhooks.

    Example:
        base_url = PublicBaseUrl("https://api.example.com")
    """

    min_length = 10
    max_length = 2048
    pattern = r"^https?://[^\s/]+(/[^\s]*)?$"


class TelegramBotAvatarDataUrl(BaseConstrainedTypedString):
    """
    A Telegram bot's profile photo, small, inlined as a data URL for the
    cabinet (its address at Telegram holds the bot token, so it is never
    handed out).

    Example:
        avatar = TelegramBotAvatarDataUrl("data:image/jpeg;base64,/9j/4AAQ")
    """

    min_length = 24
    max_length = 200_000
    pattern = r"^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/]+={0,2}$"


class TelegramBotUserId(BaseConstrainedTypedString):
    """
    Telegram's numeric id of a bot (getMe `id`), the user whose profile
    photos the Bot API lists.

    Example:
        bot_id = TelegramBotUserId("7012345678")
    """

    min_length = 1
    max_length = 20
    pattern = r"^[0-9]{1,20}$"


class TelegramBotUsername(BaseConstrainedTypedString):
    """
    Username of a Telegram bot without "@" (5 to 32 characters).

    Example:
        username = TelegramBotUsername("funicular_vr_bot")
    """

    min_length = 5
    max_length = 32
    pattern = r"^[A-Za-z][A-Za-z0-9_]{4,31}$"


class TelegramDeepLink(BaseConstrainedTypedString):
    """
    Link that opens a Telegram bot with a start parameter.

    Example:
        link = TelegramDeepLink("https://t.me/workshop_bot?start=7KQ2M9XH4D")
    """

    min_length = 20
    max_length = 128
    pattern = r"^https://t\.me/[A-Za-z][A-Za-z0-9_]{4,31}\?start=[A-Za-z0-9_\-]{1,64}$"


class TelegramWebhookSecret(BaseConstrainedTypedString):
    """
    Value Telegram repeats in X-Telegram-Bot-Api-Secret-Token.

    Example:
        secret = TelegramWebhookSecret("3f1c" * 16)
    """

    min_length = 1
    max_length = 256
    pattern = r"^[A-Za-z0-9_\-]{1,256}$"


class VoiceToolSecret(BaseConstrainedTypedString):
    """
    Per-business secret of the voice-agent webhooks (hex HMAC-SHA256).

    Example:
        secret = VoiceToolSecret("ab" * 32)
    """

    min_length = 64
    max_length = 64
    pattern = r"^[0-9a-f]{64}$"


class WhatsAppTemplateLanguageCode(BaseConstrainedTypedString):
    """
    Language of an approved WhatsApp message template ("en", "pt_BR").

    Example:
        language = WhatsAppTemplateLanguageCode("pt_BR")
    """

    min_length = 2
    max_length = 8
    pattern = r"^[a-z]{2,3}(_[A-Z]{2})?$"


class WhatsAppTemplateName(BaseConstrainedTypedString):
    """
    Name of a message template approved by Meta.

    Example:
        name = WhatsAppTemplateName("staff_notification")
    """

    min_length = 1
    max_length = 512
    pattern = r"^[a-z0-9_]{1,512}$"


class WidgetAccentColor(BaseConstrainedTypedString):
    """
    Brand colour of the website chat widget as a six-digit hex colour.

    Example:
        color = WidgetAccentColor("#0f766e")
    """

    min_length = 7
    max_length = 7
    pattern = r"^#[0-9a-fA-F]{6}$"


class WidgetDemoUrl(BaseConstrainedTypedString):
    """
    Address of the page that shows a business's website chat widget as
    visitors see it (a preview for owners).

    Example:
        demo_url = WidgetDemoUrl(
            "https://api.example.com/widget/demo?business_id=business_1"
        )
    """

    min_length = 14
    max_length = 2048
    pattern = r"^https?://[^\s/]+(/[^\s]*)?/widget/demo\?business_id=[^\s&]+$"


class WidgetErrorName(BaseConstrainedTypedString):
    """
    The JavaScript error type a website widget error was (TypeError,
    NetworkError...): a name, never the message, which may quote a page.

    Example:
        name = WidgetErrorName("TypeError")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[A-Za-z_$][A-Za-z0-9_$]*$"


class WidgetMessageText(BaseConstrainedTypedString):
    """
    Message typed into the website chat widget (1 to 4000 characters, not
    only whitespace).

    Example:
        text = WidgetMessageText("Do you have a table for four tonight?")
    """

    min_length = 1
    max_length = 4000
    pattern = r"\S"


class WidgetScriptUrl(BaseConstrainedTypedString):
    """
    Address of the chat widget script that websites embed.

    Example:
        script_url = WidgetScriptUrl("https://api.example.com/widget.js")
    """

    min_length = 14
    max_length = 2048
    pattern = r"^https?://[^\s/]+(/[^\s]*)?/widget\.js$"


class WidgetSessionKey(BaseConstrainedTypedString):
    """
    Random key the website widget keeps per visitor (the visitor identity).

    Example:
        session_key = WidgetSessionKey("v1_9f2c4e1b7a3d48c6")
    """

    min_length = 16
    max_length = 128
    pattern = r"^[A-Za-z0-9_\-]{16,128}$"


class WidgetSourceInput(BaseConstrainedTypedString):
    """
    Where a website visitor came from, as the widget read it (its script's
    data-source, else `?src=` or `?utm_source=` of the page), before the
    server reduces it to an `AcquisitionSourceTag`: any text up to 200
    characters, so a page's odd tag never refuses the visitor's message.

    Example:
        source = WidgetSourceInput("QR Tables")
    """

    max_length = 200


class WidgetStreamTicket(BaseConstrainedTypedString):
    """
    Signed, expiring pass to one visitor's live widget stream (its business,
    the visitor and the expiry under an HMAC, base64url): the visitor key
    never travels in the stream's address, only this.

    Example:
        ticket = WidgetStreamTicket("AQ" + "A" * 64)
    """

    min_length = 40
    max_length = 120
    pattern = r"^[A-Za-z0-9_\-]{40,120}$"


# Keep abc order for all non example types, if possible.
