"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AcquisitionSourceTag(BaseConstrainedTypedString):
    """
    Where a customer's conversation came from, as the platform recorded it
    when the conversation started: the tag of a shared link (`?src=` of
    the hosted page or the widget, Telegram's `start=src_<tag>`, the code
    in a wa.me greeting, Meta's `ref`), an ad (`ad-<id>`) or the number a
    caller dialled (`tel-<digits>`). Lowercase letters, digits, "_" and "-",
    up to 32 characters.

    A sibling of `ShareSourceTag` (the tag an owner puts on a link), not
    the same meaning: this one was read back from a customer's channel.

    Example:
        source = AcquisitionSourceTag("qr-tables")
    """

    min_length = 1
    max_length = 32
    pattern = r"^[a-z0-9][a-z0-9_-]{0,31}$"


class BusinessPublicSlug(BaseConstrainedTypedString):
    """
    The business's part of its public chat address (`/c/{slug}`): lowercase
    Latin letters and digits in words joined by single hyphens, 3 to 40
    characters, so it reads well on a printed card and in a QR code.

    Example:
        slug = BusinessPublicSlug("cafe-batumi")
    """

    min_length = 3
    max_length = 40
    pattern = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class HostedChatUrl(BaseConstrainedTypedString):
    """
    Address of a business's hosted chat page on the cabinet's site, maybe
    with a source tag (`?src=qr`).

    Example:
        url = HostedChatUrl("https://app.example.com/c/cafe-batumi?src=qr")
    """

    min_length = 14
    max_length = 2048
    pattern = r"^https?://[^\s/?#]+(?:/[^\s?#]*)?/c/[^\s/?#]+(?:\?[^\s#]*)?$"


class InstagramUsername(BaseConstrainedTypedString):
    """
    The public @name of an Instagram professional account, without the "@"
    (ig.me links open a chat with it).

    Example:
        username = InstagramUsername("cafe.batumi")
    """

    min_length = 1
    max_length = 30
    pattern = r"^[A-Za-z0-9._]{1,30}$"


class MetaPageUsername(BaseConstrainedTypedString):
    """
    The username of a Facebook page (m.me links open a chat with it).

    Example:
        username = MetaPageUsername("cafebatumi")
    """

    min_length = 3
    max_length = 50
    pattern = r"^[A-Za-z0-9.]{3,50}$"


class ShareLinkUrl(BaseConstrainedTypedString):
    """
    A link customers use to start a conversation with a business: a web or
    messenger address (wa.me, t.me, m.me, ig.me, the hosted chat page) or a
    `tel:` number in international format.

    Example:
        url = ShareLinkUrl("https://wa.me/995555123456")
    """

    min_length = 8
    max_length = 2048
    pattern = r"^(?:https?://[^\s/?#]+(?:[/?#][^\s]*)?|tel:\+[1-9][0-9]{6,14})$"


class ShareSourceTag(BaseConstrainedTypedString):
    """
    Where a shared link was placed (a QR code on the tables, an Instagram
    bio, a flyer): lowercase letters, digits, "_" and "-", up to 32
    characters, so the hosted page can tell the sources apart.

    Example:
        source = ShareSourceTag("qr")
    """

    min_length = 1
    max_length = 32
    pattern = r"^[a-z0-9][a-z0-9_-]{0,31}$"


class WhatsAppNumberDigits(BaseConstrainedTypedString):
    """
    A WhatsApp business number as wa.me links spell it: the international
    number without "+", spaces or punctuation.

    Example:
        number = WhatsAppNumberDigits("995555123456")
    """

    min_length = 7
    max_length = 15
    pattern = r"^[1-9][0-9]{6,14}$"


# Keep abc order for all non example types, if possible.
