"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class DeletedRowCount(BaseConstrainedTypedInt):
    """
    How many stored rows (or files) of one kind a business's deletion
    removed, or kept on purpose (the audit log, issued invoices).
    """

    ge = 0


class DeprovisionedItemCount(BaseConstrainedTypedInt):
    """
    How many things of one kind the deletion switched off at a provider: voice
    agents, bot webhooks, page subscriptions, numbers, payment schedules.
    """

    ge = 0


class OffboardAfterDays(BaseConstrainedTypedInt):
    """
    OFFBOARD_AFTER_DAYS: how many days after a subscription ended unpaid the
    business is closed automatically (then deleted after the closure's own
    30 days). At least a week, at most ten years.
    """

    ge = 7
    le = 3650


# Keep abc order for all non example types, if possible.
