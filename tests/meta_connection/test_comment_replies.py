"""Instagram comment-to-DM: from Meta's comments webhook to one private reply."""

import pytest

from app.schemas.constants.deliveries import (
    InboundEventKind,
    InboundEventStatus,
    OutboundMessageKind,
    OutboundMessageStatus,
)
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
)
from app.utilities.storage.release_gates import COMMENT_REPLIES_GATE, is_gate_open
from tests.meta_connection.comment_world import (
    INSTAGRAM_ACCOUNT,
    PAGE_TOKEN,
    REPLY,
    CommentWorld,
    comment,
    comments_webhook,
)


def events(world: CommentWorld) -> list[InboundEventDocument]:
    return world.testbed.inbound_event_collection.list_all()


@pytest.mark.usefixtures("next_release")
class TestCommentToDm:
    def test_a_keyword_comment_gets_one_private_reply(self) -> None:
        world = CommentWorld()

        outcome = world.post(comments_webhook([comment("901", "MENU please! 🙏")]))
        world.run_worker()

        assert (int(outcome.received), int(outcome.queued)) == (1, 1)
        assert world.private_replies() == [
            {"recipient": {"comment_id": "901"}, "message": {"text": REPLY}}
        ]
        sent = world.testbed.meta_transport.requests_to("/me/messages")[0]
        assert sent.headers["Authorization"] == f"Bearer {PAGE_TOKEN}"
        [event] = events(world)
        assert event.kind is InboundEventKind.COMMENT_TRIGGER
        assert event.status is InboundEventStatus.ANSWERED
        assert event.customer_message is not None
        assert str(event.customer_message.contact_name) == "nino.k"
        [message] = world.testbed.outbound_message_collection.list_all()
        assert message.kind is OutboundMessageKind.COMMENT_REPLY
        assert message.status is OutboundMessageStatus.DELIVERED
        assert message.customer is not None
        assert str(message.customer.comment_id) == "901"

    def test_a_redelivered_webhook_answers_once(self) -> None:
        world = CommentWorld()
        payload = comments_webhook([comment("902", "price list?")])

        world.post(payload)
        again = world.post(payload)
        world.run_worker()

        assert (int(again.queued), int(again.duplicates)) == (0, 1)
        assert len(world.private_replies()) == 1

    def test_other_comments_are_left_alone(self) -> None:
        world = CommentWorld()

        outcome = world.post(
            comments_webhook(
                [
                    comment("903", "Nice menus everywhere"),  # not the word
                    comment("904", "menu", author=INSTAGRAM_ACCOUNT),  # its own
                    {"field": "mentions", "value": {"comment_id": "906"}},
                ]
            )
        )
        unknown = world.post(
            comments_webhook([comment("905", "menu")], account="17841400000000999")
        )
        world.set_replies(is_on=False, keywords=["menu"])
        switched_off = world.post(comments_webhook([comment("907", "menu")]))
        world.run_worker()

        assert int(outcome.received) == 0
        assert int(unknown.received) == 0
        assert int(switched_off.received) == 0
        assert events(world) == []
        assert world.private_replies() == []

    def test_one_reply_a_day_per_person(self) -> None:
        world = CommentWorld()

        world.post(comments_webhook([comment("908", "menu"), comment("909", "menu")]))
        world.run_worker()

        assert len(world.private_replies()) == 1
        statuses = sorted(event.status.value for event in events(world))
        assert statuses == ["answered", "failed"]

    def test_sixty_replies_an_hour_per_business(self) -> None:
        world = CommentWorld()

        world.post(
            comments_webhook(
                [
                    comment(
                        str(1000 + number), "menu", author=f"17890000000{number:05}"
                    )
                    for number in range(61)
                ]
            )
        )
        world.run_worker()

        assert len(world.private_replies()) == 60
        failed = [event for event in events(world) if event.status.value == "failed"]
        assert len(failed) == 1
        assert "hour" in str(failed[0].last_error)

    def test_turned_off_before_the_worker_sends_nothing(self) -> None:
        world = CommentWorld()
        world.post(comments_webhook([comment("910", "menu")]))

        world.set_replies(is_on=False, keywords=["menu"])
        world.run_worker()

        assert world.private_replies() == []
        assert [event.status for event in events(world)] == [
            InboundEventStatus.ANSWERED
        ]

    def test_a_failed_queue_is_tried_again_without_spending_the_day(self) -> None:
        world = CommentWorld()
        world.testbed.outbound_message_repo.insert_failures.append(
            ExternalServiceError("database went away")
        )
        world.post(comments_webhook([comment("911", "menu")]))

        world.run_worker()
        world.testbed.clock.advance(120)
        world.run_worker()

        assert len(world.private_replies()) == 1

    def test_a_forged_comment_is_refused(self) -> None:
        world = CommentWorld()

        with pytest.raises(AuthenticationRequiredError):
            world.post(
                comments_webhook([comment("912", "menu")]), signature="sha256=00"
            )
        assert events(world) == []


def test_this_release_reads_comments_and_stores_nothing() -> None:
    world = CommentWorld()

    outcome = world.post(comments_webhook([comment("913", "menu")]))

    assert is_gate_open(COMMENT_REPLIES_GATE) is False
    assert int(outcome.received) == 0
    assert events(world) == []
