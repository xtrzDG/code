"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class DeliveredNotificationCount(BaseConstrainedTypedInt):
    """How many staff contacts actually received one notification."""

    ge = 0


class QuestionOccurrenceCount(BaseConstrainedTypedInt):
    """How many times customers asked the same unanswered question."""

    ge = 1


# Keep abc order for all non example types, if possible.
