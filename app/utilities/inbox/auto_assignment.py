"""
Who takes new work automatically: the members who take turns, and the one
of them with the fewest conversations waiting, ties in turn.
"""

from collections.abc import Mapping, Sequence

from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessMember
from app.schemas.typings.inbox.constrained_integers import AwaitingConversationCount
from app.schemas.typings.users.prefixed_id import UserId


def auto_assign_candidates(
    members: Sequence[BusinessMember],
    chosen: Sequence[UserId],
) -> list[UserId]:
    """
    The members who take turns, in a stable order: the chosen ones that are
    still members (in the chosen order); without a choice every staff
    member, or the owners when the business has no staff.
    """

    member_ids: list[UserId] = [member.user_id for member in members]
    if chosen:
        return [user_id for user_id in dict.fromkeys(chosen) if user_id in member_ids]

    staff: list[UserId] = [
        member.user_id for member in members if member.role is BusinessMemberRole.STAFF
    ]
    if staff:
        return staff

    return [
        member.user_id for member in members if member.role is BusinessMemberRole.OWNER
    ]


def pick_assignee(
    candidates: Sequence[UserId],
    loads: Mapping[UserId, AwaitingConversationCount],
    last_assigned: UserId | None,
) -> UserId | None:
    """
    The candidate with the fewest conversations waiting for them; among
    equals, the first after the last one assigned automatically (in the
    candidates' order), so equal members take turns. None without
    candidates.
    """

    if not candidates:
        return None

    def load(user_id: UserId) -> int:
        return int(loads.get(user_id, AwaitingConversationCount(0)))

    lowest: int = min(load(user_id) for user_id in candidates)
    start: int = (
        candidates.index(last_assigned) + 1 if last_assigned in candidates else 0
    )
    in_turn: list[UserId] = [*candidates[start:], *candidates[:start]]
    return next(user_id for user_id in in_turn if load(user_id) == lowest)
