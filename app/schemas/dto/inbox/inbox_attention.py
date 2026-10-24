"""
What waits for the team of a business, counted once for every screen: the
inbox's view tabs, the navigation badges, the browser tab's title and the
overview's queue all read these numbers, so they never disagree. Counts
only, no personal data: reading them records no view.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.users.prefixed_id import UserId


class InboxAttentionQuery(ImmutableDTO):
    """The waiting work of one business as one member sees it."""

    user_id: UserId
    business_id: BusinessId


class InboxAttentionCounts(ImmutableDTO):
    """
    Conversations waiting for the team (sandbox left out), by inbox view:
    those that need a person, those with an open request, those nobody is
    assigned to, and those assigned to the viewer; plus pending bookings
    that have not started yet and channels the platform refused. The inbox
    badge is `needs_person + requests`, the sum of its two tabs.

    The `*_count` fields are the names `/attention-counts` used before
    2026-10; they carry the same numbers and go away in /v2.
    """

    business_id: BusinessId
    needs_person: ListItemCount
    requests: ListItemCount
    unassigned: ListItemCount
    mine: ListItemCount
    unconfirmed_bookings: ListItemCount
    channel_errors: ListItemCount
    open_handoff_count: ListItemCount = Field(deprecated="Use needs_person.")
    new_lead_count: ListItemCount = Field(deprecated="Use requests.")
    unconfirmed_booking_count: ListItemCount = Field(
        deprecated="Use unconfirmed_bookings."
    )
    channel_error_count: ListItemCount = Field(deprecated="Use channel_errors.")
