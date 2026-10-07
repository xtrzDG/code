"""How the team inbox of a business shares new work."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.inbox.booleans import (
    AutoAssignNewHandoffs,
    AutoAssignNewRequests,
)
from app.schemas.typings.users.prefixed_id import UserId

# Members who take turns in the automatic assignment.
MAX_AUTO_ASSIGN_MEMBERS: int = 100


class InboxSettingsRequest(ImmutableDTO):
    """
    Body of PUT .../inbox/settings: assign new handoffs and new requests
    automatically, to the members in `auto_assign_user_ids` (empty: every
    staff member, or the owners when there is no staff).
    """

    auto_assign_new_handoffs: AutoAssignNewHandoffs = False
    auto_assign_new_requests: AutoAssignNewRequests = False
    auto_assign_user_ids: list[UserId] = Field(
        default_factory=list[UserId], max_length=MAX_AUTO_ASSIGN_MEMBERS
    )


class UpdateInboxSettingsCommand(ImmutableDTO):
    """An owner changes the auto-assignment (audited)."""

    user_id: UserId
    business_id: BusinessId
    request: InboxSettingsRequest
    client_ip_address: ClientIpAddress | None = None


class InboxSettingsQuery(ImmutableDTO):
    """The inbox settings of a business (owners and staff)."""

    user_id: UserId
    business_id: BusinessId


class InboxSettingsView(ImmutableDTO):
    """The inbox settings as stored (defaults when never changed)."""

    business_id: BusinessId
    auto_assign_new_handoffs: AutoAssignNewHandoffs = False
    auto_assign_new_requests: AutoAssignNewRequests = False
    auto_assign_user_ids: list[UserId] = Field(default_factory=list[UserId])
