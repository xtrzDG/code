"""
Links that open a conversation with a business in each channel: the hosted
chat page, WhatsApp (wa.me), Telegram (t.me), Messenger (m.me), Instagram
(ig.me/m) and a phone call (tel:).

A source tag (where the link was put: a QR code on the tables, an
Instagram bio) travels only where the platform carries it without showing
it to the customer: `?src=` on the hosted page, `?ref=` on m.me and ig.me
(Meta passes it to the page's webhook). WhatsApp would put it into the
customer's first message and Telegram would send "/start <tag>" in their
name, so those links stay untagged.
"""

from urllib.parse import quote, urlencode

from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    TelegramBotUsername,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.sharing.constrained_strings import (
    HostedChatUrl,
    InstagramUsername,
    MetaPageUsername,
    ShareLinkUrl,
    ShareSourceTag,
    WhatsAppNumberDigits,
)

HOSTED_CHAT_PATH_PREFIX: str = "/c/"
HOSTED_CHAT_PRIVACY_SUFFIX: str = "/privacy"
HOSTED_CHAT_SOURCE_PARAMETER: str = "src"
META_SOURCE_PARAMETER: str = "ref"
WHATSAPP_LINK_BASE: str = "https://wa.me/"
TELEGRAM_LINK_BASE: str = "https://t.me/"
MESSENGER_LINK_BASE: str = "https://m.me/"
INSTAGRAM_LINK_BASE: str = "https://ig.me/m/"


def build_hosted_chat_url(
    cabinet_base_url: CabinetBaseUrl,
    address: str,
    source: ShareSourceTag | None = None,
) -> HostedChatUrl:
    """`{cabinet}/c/{address}`, with `?src={source}` when tagged."""

    url: str = (
        str(cabinet_base_url).rstrip("/")
        + HOSTED_CHAT_PATH_PREFIX
        + quote(address, safe="")
    )
    return HostedChatUrl(url + source_query(HOSTED_CHAT_SOURCE_PARAMETER, source))


def build_hosted_privacy_url(cabinet_base_url: CabinetBaseUrl, address: str) -> str:
    """The platform's default privacy notice of the business's chat."""

    return (
        str(cabinet_base_url).rstrip("/")
        + HOSTED_CHAT_PATH_PREFIX
        + quote(address, safe="")
        + HOSTED_CHAT_PRIVACY_SUFFIX
    )


def build_whatsapp_link(number: WhatsAppNumberDigits) -> ShareLinkUrl:
    return ShareLinkUrl(WHATSAPP_LINK_BASE + str(number))


def build_telegram_link(username: TelegramBotUsername) -> ShareLinkUrl:
    return ShareLinkUrl(TELEGRAM_LINK_BASE + str(username).lstrip("@"))


def build_messenger_link(
    page: MetaPageUsername | MetaObjectId,
    source: ShareSourceTag | None = None,
) -> ShareLinkUrl:
    """m.me/{page username or page id}, with `?ref=` when tagged."""

    return ShareLinkUrl(
        MESSENGER_LINK_BASE
        + quote(str(page), safe="")
        + source_query(META_SOURCE_PARAMETER, source)
    )


def build_instagram_link(
    username: InstagramUsername,
    source: ShareSourceTag | None = None,
) -> ShareLinkUrl:
    return ShareLinkUrl(
        INSTAGRAM_LINK_BASE
        + quote(str(username), safe="")
        + source_query(META_SOURCE_PARAMETER, source)
    )


def build_phone_link(phone_number: E164PhoneNumber) -> ShareLinkUrl:
    return ShareLinkUrl("tel:" + str(phone_number))


def source_query(parameter: str, source: ShareSourceTag | None) -> str:
    return "" if source is None else "?" + urlencode({parameter: str(source)})
