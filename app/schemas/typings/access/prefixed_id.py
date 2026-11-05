"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class PlatformAdminId(BasePrefixedTypedId):
    """
    Identifier of one platform admin's record (a person allowed into the
    admin pages, by their sign-in phone number or e-mail, and their role).
    Derived (UUID v5) from the sign-in destination, so a person has one
    record.
    """

    prefix = "platform_admin"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class SupportAccessGrantId(BasePrefixedTypedId):
    """
    Random identifier of one support access grant: a platform admin's
    time-boxed look into a client's cabinet, or the owner's consent that
    support may also change things.
    """

    prefix = "support_access"


# Keep abc order for all non example types, if possible.
