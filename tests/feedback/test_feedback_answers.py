"""
The customer's answer to a request for feedback, through the conversation
engine: a rating is recorded and thanked by the platform itself (no model
call), everyone gets the review link whatever the score, and a score of 3
or below also hands the conversation to a colleague.
"""

from datetime import timedelta

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import LlmTurnRole, MessageAuthor
from app.schemas.constants.feedback import FeedbackRequestStatus
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.feedback.constrained_strings import ReviewLinkToken
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.feedback.feedback_keys import feedback_request_id_of
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.scripted_turns import say, scripted

REVIEW_PAGE: str = "https://g.page/r/sakhli/review"
APP_BASE_URL: str = "https://api.example.com"
TOKEN: str = "q3Jd8sLq0Pz-Xb7W2nVc1A"
TRACKED_LINK: str = f"{APP_BASE_URL}/v1/public/reviews/{TOKEN}"


def world_asked(
    *later_replies: str, app_base_url: str | None = APP_BASE_URL
) -> tuple[BrainWorld, FeedbackRequestDocument]:
    """A customer who chatted yesterday and was just asked about their visit."""

    world = build_world(
        scripted(say("Hello! How can I help?"), *(say(text) for text in later_replies)),
        app_base_url=app_base_url,
    )
    profile = world.profile_repo.get_by_business(world.business.id)
    assert profile is not None
    profile.google_review_url = WebLink(REVIEW_PAGE)
    world.profile_repo.save(profile)
    world.send("Hi")
    world.clock.advance(timedelta(hours=20))
    [contact] = world.contacts()
    now = Microseconds(world.clock.now_nanoseconds() // 1000)
    booking_id = BookingId()
    request = FeedbackRequestDocument(
        id=feedback_request_id_of(world.business.id, booking_id),
        business_id=world.business.id,
        booking_id=booking_id,
        contact_id=contact.id,
        visit_ended_at=now,
        language=LanguageTag("en"),
        status=FeedbackRequestStatus.SENT,
        channel=ChannelKind.WHATSAPP,
        review_token=ReviewLinkToken(TOKEN),
        sent_at=now,
        created_at=now,
        updated_at=now,
    )
    world.feedback_request_repo.insert_if_new(request)
    world.clock.advance(timedelta(minutes=5))
    return world, request


def stored(
    world: BrainWorld, request: FeedbackRequestDocument
) -> FeedbackRequestDocument:
    current = world.feedback_request_repo.get(world.business.id, request.id)
    assert current is not None
    return current


def model_calls(world: BrainWorld) -> int:
    """How many answers the language model wrote."""

    return sum(
        1
        for conversation in world.conversations()
        for turn in world.turns(conversation.id)
        if turn.role is LlmTurnRole.ASSISTANT
    )


class TestRatings:
    def test_a_top_rating_is_thanked_with_the_tracked_review_link(self) -> None:
        world, request = world_asked()

        reply = world.send("5")

        assert reply.text is not None
        assert TRACKED_LINK in str(reply.text)
        assert REVIEW_PAGE not in str(reply.text)
        answered = stored(world, request)
        assert answered.status is FeedbackRequestStatus.ANSWERED
        assert answered.score is not None
        assert int(answered.score) == 5
        assert answered.conversation_id == reply.conversation_id
        assert world.handoff.commands == []
        assert reply.created_handoff_ids == []
        # Only the greeting reached the language model.
        assert model_calls(world) == 1

    def test_a_low_score_creates_a_handoff(self) -> None:
        world, request = world_asked()

        reply = world.send("2, the soup was cold")

        [command] = world.handoff.commands
        assert command.reason is HandoffReason.COMPLAINT
        assert command.urgency is HandoffUrgency.LOW
        assert command.conversation_id == reply.conversation_id
        assert "2" in str(command.summary)
        assert "the soup was cold" in str(command.summary)
        assert len(reply.created_handoff_ids) == 1
        assert int(stored(world, request).score or 0) == 2
        assert model_calls(world) == 1

    @pytest.mark.parametrize("answer", ["1", "2", "3", "4", "5", "⭐⭐⭐", "4/5"])
    def test_the_link_is_sent_regardless_of_the_score(self, answer: str) -> None:
        world, _ = world_asked()

        reply = world.send(answer)

        assert reply.text is not None
        assert TRACKED_LINK in str(reply.text)

    def test_without_the_public_address_the_review_page_itself_is_sent(self) -> None:
        world, _ = world_asked(app_base_url=None)

        reply = world.send("4")

        assert REVIEW_PAGE in str(reply.text)

    def test_a_rating_is_recorded_once(self) -> None:
        world, request = world_asked("Glad to hear it!")
        world.send("5")
        world.clock.advance(timedelta(minutes=1))

        reply = world.send("1")

        assert str(reply.text) == "Glad to hear it!"
        assert int(stored(world, request).score or 0) == 5
        assert world.handoff.commands == []

    def test_a_number_after_someone_wrote_to_the_customer_is_not_a_rating(
        self,
    ) -> None:
        world, request = world_asked("Table for 3 people, at what time?")
        [conversation] = world.conversations()
        now = Microseconds(world.clock.now_nanoseconds() // 1000)
        world.message_repo.save(
            MessageDocument(
                conversation_id=conversation.id,
                business_id=world.business.id,
                direction=MessageDirection.OUTBOUND,
                author=MessageAuthor.STAFF,
                text=MessageText("How many guests will come on Friday?"),
                created_at=now,
                updated_at=now,
            )
        )
        world.clock.advance(timedelta(minutes=1))

        reply = world.send("3")

        assert str(reply.text) == "Table for 3 people, at what time?"
        assert stored(world, request).status is FeedbackRequestStatus.SENT
        assert world.handoff.commands == []

    def test_a_question_with_a_number_is_for_the_assistant(self) -> None:
        world, request = world_asked("We are open until 23:00.")

        reply = world.send("Are you open at 5?")

        assert str(reply.text) == "We are open until 23:00."
        assert stored(world, request).status is FeedbackRequestStatus.SENT

    def test_a_rating_in_another_messenger_does_not_answer_the_request(self) -> None:
        world, request = world_asked("Hello again!")

        world.send("5", channel=ChannelKind.TELEGRAM, user_id="555000111")

        assert stored(world, request).status is FeedbackRequestStatus.SENT
