"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class WaitlistEntryId(BasePrefixedTypedId):
    """
    Identifier of one customer's place on a business's waitlist (a date, a
    time window, a party and what they want to book).

    Example:
        entry_id = WaitlistEntryId()
    """

    prefix = "waitlist_entry"


class WaitlistSettingsId(BasePrefixedTypedId):
    """
    Identifier of the waitlist settings of one business.

    Derived (UUID v5) from the business, so a business has one document.
    """

    prefix = "waitlist_settings"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
