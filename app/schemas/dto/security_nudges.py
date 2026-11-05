"""The reminder to protect customers' data with a second factor (owners)."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.security_nudges import SecurityNudgeReason
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.security_nudges.booleans import (
    HasSecondFactor,
    IsSecurityNudgeShown,
    IsViewerOwner,
)
from app.schemas.typings.security_nudges.constrained_integers import TeamMemberCount
from app.schemas.typings.users.prefixed_id import UserId


class SecurityNudgeQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class DismissSecurityNudgeCommand(ImmutableDTO):
    """An owner puts the reminder away."""

    user_id: UserId
    business_id: BusinessId


class SecurityNudgeSource(ImmutableDTO):
    """A business already authorized for this person, to describe the reminder."""

    business: BusinessDocument
    user_id: UserId


class SecurityNudgeView(ImmutableDTO):
    """
    Whether the person sees the banner "Protect your customers' data: turn
    on a second factor" (`is_shown`) and why (`reason`). Shown to an owner
    of a live business who has neither a passkey nor an authenticator app
    and has not put it away; put away while working alone, it comes back
    once the team grows past one person (`team_grew`). `is_owner` tells
    whether the reminder concerns the person at all (the setup guide's
    step is an owner's only).
    """

    is_shown: IsSecurityNudgeShown
    reason: SecurityNudgeReason | None = None
    is_owner: IsViewerOwner
    has_second_factor: HasSecondFactor
    team_size: TeamMemberCount
    dismissed_at: Microseconds | None = None
