"""
How much waits in a business's inbox: the numbers on Messages in the
cabinet's navigation. Counts only, no personal data, so reading them is not
a view of anyone's data (no audit entry) and the cabinet may poll them.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import ListItemCount


class InboxCountsQuery(ImmutableDTO):
    """The waiting items of one business."""

    business_id: BusinessId


class InboxCounts(ImmutableDTO):
    """
    Handoffs nobody has resolved yet and requests still new. Sandbox activity
    (the owner's test chat, autotests) is not counted.
    """

    business_id: BusinessId
    open_handoff_count: ListItemCount
    new_lead_count: ListItemCount
