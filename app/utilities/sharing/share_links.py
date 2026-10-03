"""
The links a business shares (each channel that is switched on, the hosted
chat page first), the same links without tags for the hosted page's
"other ways to reach us", and the address of the business's privacy notice.
"""

from collections.abc import Sequence

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.sharing import ShareLinkGap, ShareLinkKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument, ChannelPublicProfile
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.channels.widget import WidgetContactLinkView
from app.schemas.dto.sharing import ShareLinkView
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    TelegramBotUsername,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.sharing.constrained_strings import (
    HostedChatUrl,
    ShareLinkUrl,
    ShareSourceTag,
)
from app.schemas.typings.sharing.strings import ShareLinkLabel
from app.utilities.channels.channel_links import (
    build_hosted_privacy_url,
    build_instagram_link,
    build_messenger_link,
    build_phone_link,
    build_telegram_link,
    build_whatsapp_link,
)

# Messengers in the order customers are offered them (free ones first, as
# in the cabinet), then a call.
CHANNEL_LINK_KINDS: tuple[tuple[ChannelKind, ShareLinkKind], ...] = (
    (ChannelKind.TELEGRAM, ShareLinkKind.TELEGRAM),
    (ChannelKind.INSTAGRAM, ShareLinkKind.INSTAGRAM),
    (ChannelKind.MESSENGER, ShareLinkKind.MESSENGER),
    (ChannelKind.WHATSAPP, ShareLinkKind.WHATSAPP),
    (ChannelKind.PHONE, ShareLinkKind.PHONE),
)


def business_address(business: BusinessDocument) -> str:
    """What follows /c/: the public slug, else the business id."""

    return str(business.public_slug or business.id)


def build_share_links(
    channels: Sequence[ChannelDocument],
    profile: BusinessProfileDocument | None,
    hosted_chat_url: HostedChatUrl | None,
    source: ShareSourceTag | None,
) -> list[ShareLinkView]:
    """The hosted page first (a gap without CABINET_BASE_URL), then channels."""

    links: list[ShareLinkView] = [
        ShareLinkView(
            kind=ShareLinkKind.HOSTED_CHAT,
            url=None if hosted_chat_url is None else ShareLinkUrl(hosted_chat_url),
            label=(
                None
                if hosted_chat_url is None
                else ShareLinkLabel(str(hosted_chat_url).split("://", 1)[-1])
            ),
            gap=ShareLinkGap.NOT_CONFIGURED if hosted_chat_url is None else None,
        )
    ]
    for channel_kind, link_kind in CHANNEL_LINK_KINDS:
        channel: ChannelDocument | None = find_connected(channels, channel_kind)
        if channel is not None:
            links.append(build_channel_link(link_kind, channel, profile, source))

    return links


def build_contact_links(
    channels: Sequence[ChannelDocument],
    profile: BusinessProfileDocument | None,
) -> list[WidgetContactLinkView]:
    """The channels' untagged links, for the hosted page's other ways."""

    return [
        WidgetContactLinkView(kind=link.kind, url=link.url)
        for link in build_share_links(channels, profile, None, None)
        if link.url is not None and link.kind is not ShareLinkKind.HOSTED_CHAT
    ]


def choose_privacy_url(
    business: BusinessDocument,
    profile: BusinessProfileDocument | None,
    cabinet_base_url: CabinetBaseUrl | None,
) -> WebLink | None:
    """
    The business's own privacy notice, else the platform's default notice
    for its chat (None while CABINET_BASE_URL is not set).
    """

    if profile is not None and profile.privacy_notice_url is not None:
        return profile.privacy_notice_url

    if cabinet_base_url is None:
        return None

    return WebLink(
        build_hosted_privacy_url(cabinet_base_url, business_address(business))
    )


def find_connected(
    channels: Sequence[ChannelDocument],
    kind: ChannelKind,
) -> ChannelDocument | None:
    for channel in channels:
        if channel.kind is kind and channel.status is ChannelStatus.CONNECTED:
            return channel

    return None


def build_channel_link(
    kind: ShareLinkKind,
    channel: ChannelDocument,
    profile: BusinessProfileDocument | None,
    source: ShareSourceTag | None,
) -> ShareLinkView:
    """A connected channel's link, or a gap when its address is unknown."""

    public: ChannelPublicProfile = channel.public_profile or ChannelPublicProfile()
    account: str = "" if channel.external_id is None else str(channel.external_id)
    match kind:
        case ShareLinkKind.TELEGRAM if is_valid(TelegramBotUsername, account):
            username = TelegramBotUsername(account)
            return linked(kind, build_telegram_link(username), f"@{username}")
        case ShareLinkKind.WHATSAPP if public.whatsapp_number is not None:
            number = public.whatsapp_number
            return linked(kind, build_whatsapp_link(number), f"+{number}")
        case ShareLinkKind.INSTAGRAM if public.instagram_username is not None:
            username_text = public.instagram_username
            return linked(
                kind, build_instagram_link(username_text, source), f"@{username_text}"
            )
        case ShareLinkKind.MESSENGER if public.page_username is not None:
            page = public.page_username
            return linked(kind, build_messenger_link(page, source), str(page))
        case ShareLinkKind.MESSENGER if is_valid(MetaObjectId, account):
            return linked(
                kind, build_messenger_link(MetaObjectId(account), source), None
            )
        case ShareLinkKind.PHONE:
            phone: E164PhoneNumber | None = phone_to_share(channel, profile)
            if phone is not None:
                return linked(kind, build_phone_link(phone), str(phone))
        case _:
            pass

    return ShareLinkView(kind=kind, gap=ShareLinkGap.RECONNECT_CHANNEL)


def phone_to_share(
    channel: ChannelDocument,
    profile: BusinessProfileDocument | None,
) -> E164PhoneNumber | None:
    """
    The business's public number (it forwards unanswered calls to the
    assistant), else the assistant line itself.
    """

    if profile is not None and profile.contacts.public_phone_number is not None:
        return profile.contacts.public_phone_number

    account: str = "" if channel.external_id is None else str(channel.external_id)
    return E164PhoneNumber(account) if is_valid(E164PhoneNumber, account) else None


def linked(
    kind: ShareLinkKind,
    url: object,
    label: str | None,
) -> ShareLinkView:
    return ShareLinkView.model_validate({"kind": kind, "url": url, "label": label})


def is_valid(primitive: type, value: str) -> bool:
    try:
        primitive(value)
    except ValueError:
        return False

    return True
