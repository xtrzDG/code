"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class PhoneTestUrl(BaseConstrainedTypedString):
    """
    Link an owner opens on their phone to talk to their own assistant: the
    hosted website chat page or a messenger deep link (t.me).

    Example:
        link = PhoneTestUrl("https://t.me/funicular_vr_bot")
    """

    min_length = 10
    max_length = 2048
    pattern = r"^https://[^\s/]+(/[^\s]*)?$"


class StarterEntryKey(BaseConstrainedTypedString):
    """
    Snake-case key of one starter suggestion of a niche (a frequent
    question or an offer example), stable across languages.

    Example:
        key = StarterEntryKey("parking")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"


# Keep abc order for all non example types, if possible.
