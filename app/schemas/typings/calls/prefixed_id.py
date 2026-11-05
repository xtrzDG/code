"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class CallSettingsId(BasePrefixedTypedId):
    """
    Identifier of the call follow-up settings of one business.

    Derived (UUID v5) from the business, so a business has one settings
    document.
    """

    prefix = "call_settings"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class MissedCallId(BasePrefixedTypedId):
    """
    Identifier of one call whose caller did not get through.

    Derived (UUID v5) from the business, the reporting source and the
    provider's call id, so a repeated report is the same missed call.
    """

    prefix = "missed_call"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
