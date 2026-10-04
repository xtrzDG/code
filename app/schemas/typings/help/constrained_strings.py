"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ChangelogEntryKey(BaseConstrainedTypedString):
    """
    The key of one entry of the cabinet's "What's new" changelog: its
    publication day and a short slug (web/content/changelog). Keys sort by
    day, so the newest entry a person read is the largest key.

    Example:
        key = ChangelogEntryKey("2026-10-04-help-center")
    """

    min_length = 10
    max_length = 80
    pattern = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}(-[a-z0-9]+)*$"


class CoachMarkKey(BaseConstrainedTypedString):
    """
    Which one-time hint of the cabinet a person has seen (the inbox, the
    assistant, the channels page): a short lowercase name the cabinet
    chooses.

    Example:
        key = CoachMarkKey("inbox")
    """

    min_length = 2
    max_length = 40
    pattern = r"^[a-z][a-z0-9_]*$"


class HelpArticleSlug(BaseConstrainedTypedString):
    """
    The address of a help article, the same in every language (the file
    name under docs/help/<language>/).

    Example:
        slug = HelpArticleSlug("call-forwarding")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class HelpSearchText(BaseConstrainedTypedString):
    """
    What an owner typed into the help center's search box (at least one
    visible character).

    Example:
        text = HelpSearchText("переадресация")
    """

    min_length = 1
    max_length = 120
    pattern = r"\S"


class SupportLinkUrl(BaseConstrainedTypedString):
    """
    A link that opens a conversation with the platform's support: a
    WhatsApp chat (wa.me), a Telegram chat (t.me) or an e-mail (mailto:).

    Example:
        link = SupportLinkUrl("https://wa.me/995322000000")
    """

    min_length = 10
    max_length = 300
    pattern = r"^(https://(wa\.me|t\.me)/[^\s]+|mailto:[^\s@]+@[^\s@]+)$"


class SupportTelegramUsername(BaseConstrainedTypedString):
    """
    The Telegram username of the platform's support (a person or a bot),
    without "@" (SUPPORT_TELEGRAM).

    Example:
        username = SupportTelegramUsername("workshop_support")
    """

    min_length = 5
    max_length = 32
    pattern = r"^[A-Za-z][A-Za-z0-9_]{4,31}$"


# Keep abc order for all non example types, if possible.
