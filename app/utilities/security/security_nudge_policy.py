"""When an owner is reminded to protect their customers' data with a second factor."""

from app.schemas.constants.security_nudges import SecurityNudgeReason
from app.schemas.domain.security_nudges import SecurityNudgeDocument
from app.schemas.typings.security_nudges.constrained_integers import TeamMemberCount

# A team "grows past one person" when it has more than this many members.
ALONE: int = 1


def security_nudge_reason(
    *,
    is_owner: bool,
    is_live: bool,
    has_second_factor: bool,
    team_size: TeamMemberCount,
    nudge: SecurityNudgeDocument | None,
) -> SecurityNudgeReason | None:
    """
    Why the owner sees the reminder now, or None: only owners of a live
    business without a second factor see it; once put away it stays away,
    unless it was put away by an owner working alone and the team has
    grown past one person since.
    """

    if not is_owner or not is_live or has_second_factor:
        return None

    if nudge is None:
        return SecurityNudgeReason.PROTECT_CUSTOMERS

    if int(nudge.team_size_at_dismissal) <= ALONE < int(team_size):
        return SecurityNudgeReason.TEAM_GREW

    return None
