"""
The inbox badge and the inbox tabs come from one count: the badge is the sum
of the two tabs that wait for the team, and each tab's number is how many
conversations its list holds, for every member.
"""

from app.schemas.constants.inbox import InboxView
from app.schemas.dto.inbox.inbox_attention import (
    InboxAttentionCounts,
    InboxAttentionQuery,
)
from app.schemas.dto.inbox.inbox_views import InboxPage, InboxQuery
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.users.prefixed_id import UserId
from tests.inbox.inbox_scene import InboxScene, build_scene

VIEW_COUNTS: dict[InboxView, str] = {
    InboxView.NEEDS_PERSON: "needs_person",
    InboxView.REQUESTS: "requests",
    InboxView.MINE: "mine",
    InboxView.UNASSIGNED: "unassigned",
}


def listed(scene: InboxScene, view: InboxView, viewer: UserId) -> InboxPage:
    world = scene.world
    return world.list_inbox().run(
        InboxQuery(
            user_id=viewer,
            business_id=world.business.id,
            view=view,
            page=PageRequest(size=PageSize(50)),
        )
    )


def counted(scene: InboxScene, viewer: UserId) -> InboxAttentionCounts:
    world = scene.world
    return world.count_attention().run(
        InboxAttentionQuery(user_id=viewer, business_id=world.business.id)
    )


def inbox_badge(counts: InboxAttentionCounts) -> int:
    """What the cabinet's pageBadge('inbox') shows (web/src/lib/inboxBadges.ts)."""

    return int(counts.needs_person) + int(counts.requests)


def test_each_view_count_is_the_length_of_its_list() -> None:
    scene = build_scene()
    world = scene.world

    for viewer in (world.owner.id, world.staff.id, world.colleague.id):
        counts = counted(scene, viewer)
        for view, field in VIEW_COUNTS.items():
            assert len(listed(scene, view, viewer).items) == int(getattr(counts, field))


def test_the_badge_is_the_sum_of_the_two_waiting_tabs() -> None:
    scene = build_scene()
    world = scene.world

    counts = counted(scene, world.staff.id)
    tabs = len(listed(scene, InboxView.NEEDS_PERSON, world.staff.id).items) + len(
        listed(scene, InboxView.REQUESTS, world.staff.id).items
    )

    # needs a person: 3 (the test chat is left out); open requests: 3.
    assert (int(counts.needs_person), int(counts.requests)) == (3, 3)
    assert inbox_badge(counts) == tabs == 6


def test_the_list_page_and_the_badge_agree() -> None:
    scene = build_scene()
    world = scene.world

    counts = counted(scene, world.staff.id)
    page_counts = listed(scene, InboxView.ALL, world.staff.id).counts

    assert (
        page_counts.needs_person,
        page_counts.requests,
        page_counts.mine,
        page_counts.unassigned,
    ) == (counts.needs_person, counts.requests, counts.mine, counts.unassigned)


def test_the_deprecated_names_carry_the_same_numbers() -> None:
    scene = build_scene()

    counts = counted(scene, scene.world.staff.id).model_dump()

    assert counts["open_handoff_count"] == counts["needs_person"]
    assert counts["new_lead_count"] == counts["requests"]
    assert counts["unconfirmed_booking_count"] == counts["unconfirmed_bookings"]
    assert counts["channel_error_count"] == counts["channel_errors"]
