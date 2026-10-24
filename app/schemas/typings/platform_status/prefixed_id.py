"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class AnnouncementId(BasePrefixedTypedId):
    """Random identifier of one platform announcement (banner and status notice)."""

    prefix = "announcement"


# Keep abc order for all non example types, if possible.
