"""
Comment-to-DM leaves alone the people the business must not message: a
customer the owner blocked, one who said STOP, and one whose STOP outlived
their erasure (the suppression list).
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventStatus
from app.schemas.domain.contacts import ChannelIdentity, ContactBlock, ContactDocument
from app.schemas.typings.conversations.strings import ChannelUserId
from app.utilities.privacy.suppressed_identities import channel_identity
from tests.meta_connection.comment_world import (
    REPLY,
    CommentWorld,
    comment,
    comments_webhook,
)

AUTHOR: str = "1789000000000001"


def author_contact(
    world: CommentWorld,
    *,
    blocked: bool = False,
    opted_out: bool = False,
) -> ContactDocument:
    now: Microseconds = world.testbed.wall_clock.now_unix()
    owner = world.testbed.add_user("blocking-owner")
    contact = ContactDocument(
        business_id=world.business.id,
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.INSTAGRAM,
                channel_user_id=ChannelUserId(AUTHOR),
            )
        ],
        opted_out_channels=[ChannelKind.INSTAGRAM] if opted_out else [],
        block=ContactBlock(blocked_at=now, blocked_by=owner) if blocked else None,
        created_at=now,
        updated_at=now,
    )
    world.testbed.contact_repo.save(contact)
    return contact


def answer_comment(world: CommentWorld) -> None:
    world.post(comments_webhook([comment("911", "menu please")]))
    world.run_worker()


@pytest.mark.usefixtures("next_release")
class TestSilencedAuthors:
    def test_a_blocked_customer_gets_no_private_reply(self) -> None:
        world = CommentWorld()
        author_contact(world, blocked=True)

        answer_comment(world)

        assert world.private_replies() == []
        assert world.testbed.outbound_message_collection.list_all() == []
        [event] = world.testbed.inbound_event_collection.list_all()
        assert event.status is InboundEventStatus.ANSWERED

    def test_a_customer_who_said_stop_gets_no_private_reply(self) -> None:
        world = CommentWorld()
        author_contact(world, opted_out=True)

        answer_comment(world)

        assert world.private_replies() == []

    def test_a_stop_kept_after_erasure_still_counts(self) -> None:
        world = CommentWorld()
        world.testbed.suppression_list.suppress(
            world.business.id,
            [channel_identity(ChannelKind.INSTAGRAM, ChannelUserId(AUTHOR))],
            world.testbed.wall_clock.now_unix(),
        )

        answer_comment(world)

        assert world.private_replies() == []

    def test_a_known_customer_in_good_standing_is_answered(self) -> None:
        world = CommentWorld()
        author_contact(world)

        answer_comment(world)

        assert world.private_replies() == [
            {"recipient": {"comment_id": "911"}, "message": {"text": REPLY}}
        ]
