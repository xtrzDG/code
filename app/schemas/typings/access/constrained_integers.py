"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class PlatformAdminCount(BaseConstrainedTypedInt):
    """How many people hold a platform admin role (or one role)."""

    ge = 0


class SupportAccessMinutes(BaseConstrainedTypedInt):
    """How long one support look into a client's cabinet lasts, in minutes."""

    ge = 5
    le = 240


class SupportWriteAccessHours(BaseConstrainedTypedInt):
    """
    For how many hours the owner lets platform support change things in
    their cabinet (the consent then ends by itself).
    """

    ge = 1
    le = 168


# Keep abc order for all non example types, if possible.
