"""
A bad rating says why and which answer it is about; the review is its own
write, so a customer turn answered meanwhile never undoes it.
"""

import pytest

from app.schemas.constants.conversations import (
    ConversationRating,
    ConversationRatingReason,
    MessageAuthor,
)
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversation_feed.conversation_actions import (
    RateConversationCommand,
)
from app.schemas.dto.conversation_feed.conversation_views import (
    ConversationSummaryView,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from tests.brain.scripted_turns import say
from tests.teaching.teaching_world import TeachingWorld, build_teaching_world


def rate(
    world: TeachingWorld,
    conversation_id: ConversationId,
    rating: ConversationRating | None,
    reason: ConversationRatingReason | None = None,
    message_id: MessageId | None = None,
) -> ConversationSummaryView:
    world.advance(60)
    return world.rate.run(
        RateConversationCommand(
            user_id=world.brain.staff_id,
            business_id=world.brain.business.id,
            conversation_id=conversation_id,
            rating=rating,
            reason=reason,
            message_id=message_id,
        )
    )


def stored(
    world: TeachingWorld, conversation_id: ConversationId
) -> ConversationDocument:
    conversation = world.brain.conversation_repo.get(
        world.brain.business.id, conversation_id
    )
    assert conversation is not None
    return conversation


def test_a_bad_rating_names_its_reason_and_the_latest_answer() -> None:
    world = build_teaching_world(say("Первый ответ."), say("Второй ответ."))
    world.brain.send("Вопрос один")
    reply = world.brain.send("Вопрос два")

    summary = rate(
        world,
        reply.conversation_id,
        ConversationRating.BAD,
        ConversationRatingReason.WRONG_INFO,
    )

    latest = world.answer_of(reply)
    assert summary.rating is ConversationRating.BAD
    assert summary.rating_reason is ConversationRatingReason.WRONG_INFO
    assert summary.rated_message_id == latest.id
    conversation = stored(world, reply.conversation_id)
    assert conversation.awaits_improvement is True
    assert conversation.rated_by == world.brain.staff_id


def test_a_bad_rating_may_name_an_earlier_answer() -> None:
    world = build_teaching_world(say("Первый ответ."), say("Второй ответ."))
    first = world.answer_of(world.brain.send("Вопрос один"))
    reply = world.brain.send("Вопрос два")

    summary = rate(
        world,
        reply.conversation_id,
        ConversationRating.BAD,
        ConversationRatingReason.TOO_LONG,
        first.id,
    )

    assert summary.rated_message_id == first.id


def test_a_reason_belongs_only_to_a_bad_rating_of_an_answer() -> None:
    world = build_teaching_world(say("Ответ."))
    reply = world.brain.send("Вопрос")
    customer = next(
        message
        for message in world.messages(reply.conversation_id)
        if message.author is MessageAuthor.CUSTOMER
    )

    with pytest.raises(ValidationFailedError):
        rate(
            world,
            reply.conversation_id,
            ConversationRating.GOOD,
            ConversationRatingReason.TONE,
        )
    with pytest.raises(ValidationFailedError):
        rate(world, reply.conversation_id, ConversationRating.BAD, None, customer.id)
    with pytest.raises(NotFoundError):
        rate(world, reply.conversation_id, ConversationRating.BAD, None, MessageId())
    with pytest.raises(NotFoundError):
        rate(world, ConversationId(), ConversationRating.BAD)


def test_a_good_rating_or_none_clears_the_review() -> None:
    world = build_teaching_world(say("Ответ."))
    reply = world.brain.send("Вопрос")
    rate(
        world,
        reply.conversation_id,
        ConversationRating.BAD,
        ConversationRatingReason.SHOULD_HAND_OFF,
    )

    good = rate(world, reply.conversation_id, ConversationRating.GOOD)

    assert good.rating_reason is None
    assert good.rated_message_id is None
    assert stored(world, reply.conversation_id).awaits_improvement is False
    cleared = rate(world, reply.conversation_id, None)
    assert cleared.rating is None
    assert stored(world, reply.conversation_id).rated_by is None


def test_a_customer_turn_answered_meanwhile_keeps_the_review() -> None:
    world = build_teaching_world(say("Ответ."), say("Ещё ответ."))
    reply = world.brain.send("Вопрос")
    rate(
        world,
        reply.conversation_id,
        ConversationRating.BAD,
        ConversationRatingReason.WRONG_INFO,
    )

    world.brain.send("И ещё вопрос")

    conversation = stored(world, reply.conversation_id)
    assert conversation.rating is ConversationRating.BAD
    assert conversation.rating_reason is ConversationRatingReason.WRONG_INFO
    assert conversation.awaits_improvement is True


def test_a_rated_test_chat_never_waits_for_improvement() -> None:
    world = build_teaching_world(say("Ответ."))
    reply = world.brain.send("Вопрос", is_sandbox=True, user_id="owner-test")

    rate(world, reply.conversation_id, ConversationRating.BAD)

    assert stored(world, reply.conversation_id).awaits_improvement is False
