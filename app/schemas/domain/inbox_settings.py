from base_pydantic_schemas import BaseDocument
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.inbox.booleans import (
    AutoAssignNewHandoffs,
    AutoAssignNewRequests,
)
from app.schemas.typings.inbox.prefixed_id import InboxSettingsId
from app.schemas.typings.users.prefixed_id import UserId


class InboxSettingsDocument(BaseDocument):
    """
    How the team inbox of one business shares new work (one document per
    business, the id derived from it).

    With auto-assignment on, a new handoff (or request) of a conversation
    nobody is assigned goes to the member of `auto_assign_user_ids` (empty:
    every staff member, or the owners when there is no staff) with the
    fewest conversations waiting for them; ties take turns after
    `last_auto_assigned_user_id`.
    """

    id: InboxSettingsId
    business_id: BusinessId
    auto_assign_new_handoffs: AutoAssignNewHandoffs = False
    auto_assign_new_requests: AutoAssignNewRequests = False
    auto_assign_user_ids: list[UserId] = Field(default_factory=list[UserId])
    last_auto_assigned_user_id: UserId | None = None
