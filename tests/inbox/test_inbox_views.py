"""The views of the team inbox, their counts, paging and the audit per viewer."""

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.inbox import InboxView
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.inbox.inbox_attention import InboxAttentionQuery
from app.schemas.dto.inbox.inbox_views import InboxPage, InboxQuery, InboxViewCounts
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.platform.constrained_integers import ListItemCount, PageSize
from app.schemas.typings.users.prefixed_id import UserId
from tests.inbox.inbox_scene import InboxScene, build_scene


def page(
    scene: InboxScene,
    view: InboxView,
    viewer: UserId | None = None,
    channel: ChannelKind | None = None,
    size: int = 50,
    cursor: str | None = None,
) -> InboxPage:
    world = scene.world
    return world.list_inbox().run(
        InboxQuery.model_validate(
            {
                "user_id": viewer or world.staff.id,
                "business_id": world.business.id,
                "view": view,
                "channel": channel,
                "page": PageRequest.model_validate(
                    {"size": PageSize(size), "cursor": cursor}
                ),
            }
        )
    )


def ids(conversations: list[ConversationDocument]) -> list[str]:
    return [str(conversation.id) for conversation in conversations]


def listed(result: InboxPage) -> list[str]:
    return [str(item.id) for item in result.items]


@pytest.fixture(name="scene")
def build() -> InboxScene:
    return build_scene()


def test_each_view_lists_its_conversations_latest_message_first(
    scene: InboxScene,
) -> None:
    assert listed(page(scene, InboxView.NEEDS_PERSON)) == ids(
        [scene.mine_handoff, scene.unassigned_handoff, scene.both]
    )
    assert listed(page(scene, InboxView.REQUESTS)) == ids(
        [scene.ana_request, scene.unassigned_request, scene.both]
    )
    assert listed(page(scene, InboxView.MINE)) == ids([scene.mine_handoff])
    assert listed(page(scene, InboxView.UNASSIGNED)) == ids(
        [scene.unassigned_handoff, scene.unassigned_request, scene.both]
    )
    assert listed(page(scene, InboxView.ALL)) == ids(
        [
            scene.mine_handoff,
            scene.ana_request,
            scene.unassigned_handoff,
            scene.unassigned_request,
            scene.both,
            scene.won_request,
            scene.quiet,
        ]
    )


def test_mine_is_the_viewers_own(scene: InboxScene) -> None:
    world = scene.world

    assert listed(page(scene, InboxView.MINE, viewer=world.colleague.id)) == ids(
        [scene.ana_request]
    )
    assert listed(page(scene, InboxView.MINE, viewer=world.owner.id)) == []


def test_the_counts_of_each_view(scene: InboxScene) -> None:
    world = scene.world
    expected = InboxViewCounts(
        needs_person=ListItemCount(3),
        requests=ListItemCount(3),
        mine=ListItemCount(1),
        unassigned=ListItemCount(3),
    )

    assert page(scene, InboxView.ALL).counts == expected
    for viewer, mine in ((world.staff.id, 1), (world.owner.id, 0)):
        counts = world.count_attention().run(
            InboxAttentionQuery(user_id=viewer, business_id=world.business.id)
        )
        assert InboxViewCounts(
            needs_person=counts.needs_person,
            requests=counts.requests,
            mine=counts.mine,
            unassigned=counts.unassigned,
        ) == expected.model_copy(update={"mine": ListItemCount(mine)})


def test_the_counts_follow_a_resolution(scene: InboxScene) -> None:
    world = scene.world
    resolved = world.conversation_repo.get(world.business.id, scene.mine_handoff.id)
    assert resolved is not None
    resolved.status = resolved.status.OPEN
    world.conversation_repo.save(resolved)

    counts = page(scene, InboxView.MINE).counts

    assert (counts.needs_person, counts.mine) == (ListItemCount(2), ListItemCount(0))
    assert listed(page(scene, InboxView.MINE)) == []


def test_pages_follow_the_cursor_without_gaps_or_repeats(scene: InboxScene) -> None:
    first = page(scene, InboxView.ALL, size=3)
    second = page(scene, InboxView.ALL, size=3, cursor=first.next_cursor)
    third = page(scene, InboxView.ALL, size=3, cursor=second.next_cursor)

    assert first.next_cursor is not None and second.next_cursor is not None
    assert third.next_cursor is None
    assert listed(first) + listed(second) + listed(third) == listed(
        page(scene, InboxView.ALL)
    )


def test_a_channel_narrows_the_view(scene: InboxScene) -> None:
    assert listed(page(scene, InboxView.REQUESTS, channel=ChannelKind.WHATSAPP)) == ids(
        [scene.ana_request, scene.both]
    )


def test_every_page_is_audited_as_the_viewers_view(scene: InboxScene) -> None:
    world = scene.world
    page(scene, InboxView.UNASSIGNED)
    page(scene, InboxView.MINE, viewer=world.owner.id)

    views = [
        (entry.actor_id, str(entry.entity_id))
        for entry in world.audit_entries()
        if entry.action is AuditAction.VIEW and str(entry.entity) == "inbox"
    ]
    assert views == [(world.staff.id, "unassigned"), (world.owner.id, "mine")]
