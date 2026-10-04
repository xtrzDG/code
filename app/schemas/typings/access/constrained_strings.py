"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class SupportAccessReason(BaseConstrainedTypedString):
    """
    Why a platform admin opens a client's cabinet, in their own words; the
    owner reads it in the cabinet's banner and the audit log keeps it.

    Example:
        reason = SupportAccessReason("Owner asked why bookings stopped (ticket 214)")
    """

    min_length = 8
    max_length = 300
    pattern = r"^\S[\s\S]*\S$"


# Keep abc order for all non example types, if possible.
