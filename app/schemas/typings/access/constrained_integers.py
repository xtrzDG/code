"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class SupportWriteAccessHours(BaseConstrainedTypedInt):
    """
    For how many hours the owner lets platform support change things in
    their cabinet (the consent then ends by itself).
    """

    ge = 1
    le = 168


# Keep abc order for all non example types, if possible.
