"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class BusinessLimitsId(BasePrefixedTypedId):
    """
    Identifier of the limits of one business (its daily spend ceilings and
    the websites allowed to show its chat).

    Derived (UUID v5) from the business, so a business has one limits
    document and reading it is one read by id.
    """

    prefix = "business_limits"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class SpendLimitMarkId(BasePrefixedTypedId):
    """
    Identifier of the mark that one business passed one of its spend limits
    on one of its days.

    Derived (UUID v5) from the business, the day and the limit, so only the
    first of several processes that see the limit passed stores it and
    tells the team.
    """

    prefix = "spend_limit_mark"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5
