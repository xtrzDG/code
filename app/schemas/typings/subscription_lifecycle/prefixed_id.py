"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class SubscriptionEventId(BasePrefixedTypedId):
    """
    Identifier of one step of a subscription's life: a cancellation with
    its reason, an accepted offer, a pause scheduled, started or ended, a
    win-back message sent. A win-back step's id derives (UUID v5) from the
    subscription and the stage, so each stage is recorded once.

    Example:
        event_id = SubscriptionEventId()
    """

    prefix = "subscription_event"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


# Keep abc order for all non example types, if possible.
