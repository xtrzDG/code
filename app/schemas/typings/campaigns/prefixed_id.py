"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class CampaignMessageId(BasePrefixedTypedId):
    """
    Identifier of one invitation of a rebooking campaign (or one pre-arrival
    note) to one customer.

    Derived (UUID v5) from the business, the rule and the booking it is
    about, so a visit leads to at most one invitation however often the
    job looks at it.
    """

    prefix = "campaign_message"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class CampaignSettingsId(BasePrefixedTypedId):
    """
    Identifier of the rebooking campaign settings of one business.

    Derived (UUID v5) from the business, so a business has one document.
    """

    prefix = "campaign_settings"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
