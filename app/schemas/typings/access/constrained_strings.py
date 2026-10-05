"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AdminActionReason(BaseConstrainedTypedString):
    """
    Why a platform admin changed a client's account (a longer trial, a
    discount, credit, a waived setup fee, a payment recorded by hand, a
    plan set by hand), in their own words; the audit log keeps it with
    the action.

    Example:
        reason = AdminActionReason("Slow onboarding: menu photos arrive next week")
    """

    min_length = 8
    max_length = 300
    pattern = r"^\S[\s\S]*\S$"


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
