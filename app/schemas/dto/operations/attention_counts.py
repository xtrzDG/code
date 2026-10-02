"""
What waits for a person in a business: the badges of the cabinet's
navigation and the unread count in the browser tab. Counts only, no
personal data, so reading them is not a view of anyone's data (no audit
entry); the cabinet reloads them when the live stream reports a change.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import ListItemCount


class AttentionCountsQuery(ImmutableDTO):
    """The waiting items of one business."""

    business_id: BusinessId


class AttentionCounts(ImmutableDTO):
    """
    Handoffs nobody has resolved yet, requests still new, bookings still
    waiting for confirmation and channels the platform refused. Sandbox
    activity (the owner's test chat, autotests) is not counted.
    """

    business_id: BusinessId
    open_handoff_count: ListItemCount
    new_lead_count: ListItemCount
    unconfirmed_booking_count: ListItemCount
    channel_error_count: ListItemCount
