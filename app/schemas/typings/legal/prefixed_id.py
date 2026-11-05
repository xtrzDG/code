"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class SubprocessorAnnouncementId(BasePrefixedTypedId):
    """
    Identifier of the announcement of one sub-processor change to every
    business. Derived (UUID v5) from the change key: one per change.
    """

    prefix = "subprocessor_announcement"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class SubprocessorNoticeId(BasePrefixedTypedId):
    """
    Identifier of the notice one business got about one sub-processor
    change. Derived (UUID v5) from both: one notice per business and change.
    """

    prefix = "subprocessor_notice"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
