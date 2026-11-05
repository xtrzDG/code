"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AnnouncementText(BaseConstrainedTypedString):
    """
    What the platform team tells every owner about the platform's state in
    one language: the banner over the cabinet and the status page's notice
    (an outage, slow answers, planned maintenance).

    Example:
        text = AnnouncementText("WhatsApp replies are delayed by a few minutes.")
    """

    min_length = 3
    max_length = 600
    pattern = r"^\S(.*\S)?\Z"


class StatusDay(BaseConstrainedTypedString):
    """
    A calendar day in UTC of the status page's history.

    Example:
        day = StatusDay("2026-10-04")
    """

    min_length = 10
    max_length = 10
    pattern = r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"


# Keep abc order for all non example types, if possible.
