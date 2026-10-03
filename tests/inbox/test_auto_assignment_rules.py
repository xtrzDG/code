"""Who takes new work: the candidates and the turn among equals."""

from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessMember
from app.schemas.typings.inbox.constrained_integers import AwaitingConversationCount
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.inbox.auto_assignment import auto_assign_candidates, pick_assignee

OWNER, NINO, GIORGI, ANA = UserId(), UserId(), UserId(), UserId()
TEAM: list[BusinessMember] = [
    BusinessMember(user_id=OWNER, role=BusinessMemberRole.OWNER),
    BusinessMember(user_id=NINO, role=BusinessMemberRole.STAFF),
    BusinessMember(user_id=GIORGI, role=BusinessMemberRole.STAFF),
]


def load(**counts: int) -> dict[UserId, AwaitingConversationCount]:
    people = {"owner": OWNER, "nino": NINO, "giorgi": GIORGI, "ana": ANA}
    return {
        people[name]: AwaitingConversationCount(count) for name, count in counts.items()
    }


def test_without_a_choice_the_staff_take_turns() -> None:
    assert auto_assign_candidates(TEAM, []) == [NINO, GIORGI]


def test_a_choice_keeps_its_order_drops_strangers_and_repeats() -> None:
    assert auto_assign_candidates(TEAM, [GIORGI, ANA, OWNER, GIORGI]) == [
        GIORGI,
        OWNER,
    ]


def test_without_staff_the_owners_take_new_work() -> None:
    assert auto_assign_candidates(TEAM[:1], []) == [OWNER]


def test_the_least_busy_candidate_is_picked() -> None:
    assert pick_assignee([NINO, GIORGI], load(nino=3, giorgi=1), None) == GIORGI


def test_equals_take_turns_after_the_last_one() -> None:
    candidates = [NINO, GIORGI, OWNER]

    assert pick_assignee(candidates, {}, None) == NINO
    assert pick_assignee(candidates, {}, NINO) == GIORGI
    assert pick_assignee(candidates, {}, OWNER) == NINO
    assert pick_assignee(candidates, load(giorgi=2), NINO) == OWNER
    assert pick_assignee(candidates, {}, ANA) == NINO


def test_nobody_to_pick_is_none() -> None:
    assert pick_assignee([], {}, None) is None
