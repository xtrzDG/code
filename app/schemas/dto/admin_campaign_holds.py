"""The platform admin's review of campaigns held over their opt-out rate (ABUSE-05)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.typings.access.constrained_strings import AdminActionReason
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.campaigns.constrained_integers import CampaignMessageCount
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId


class CampaignHoldView(ImmutableDTO):
    """One held campaign: its business, when it was held, and the figures."""

    business_id: BusinessId
    held_at: Microseconds
    sent: CampaignMessageCount
    opted_out: CampaignMessageCount


class CampaignHoldList(ImmutableDTO):
    items: list[CampaignHoldView] = Field(default_factory=list[CampaignHoldView])


class ListCampaignHoldsQuery(ImmutableDTO):
    user_id: UserId


class ReleaseCampaignHoldCommand(ImmutableDTO):
    """A platform admin lets a held campaign write again, with the reason."""

    user_id: UserId
    business_id: BusinessId
    reason: AdminActionReason
    client_ip_address: ClientIpAddress | None = None
