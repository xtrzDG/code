"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class SecurityNudgeId(BasePrefixedTypedId):
    """
    The owner's answer to the "turn on a second factor" reminder in one
    business: derived (UUID v5) from the business and the person, so each
    pair has one.
    """

    prefix = "security_nudge"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


# Keep abc order for all non example types, if possible.
