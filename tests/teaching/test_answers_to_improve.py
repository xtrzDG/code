"""
The Overview's "Answers worth improving": bad ratings nobody acted on yet,
then the questions the assistant could not answer.
"""

import pytest

from app.schemas.constants.assistants import AutotestCaseSource, AutotestExpectation
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import (
    AnswerToImproveKind,
    ConversationRating,
    ConversationRatingReason,
)
from app.schemas.constants.knowledge import AnswerCorrectionScope
from app.schemas.dto.assistants.autotest_cases import (
    AutotestCaseInput,
    CreateAutotestCaseCommand,
)
from app.schemas.dto.conversation_feed.answers_to_improve import (
    AnswersToImproveQuery,
    AnswersToImproveView,
)
from app.schemas.dto.conversation_feed.conversation_actions import (
    RateConversationCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.assistants.constrained_strings import AutotestCaseQuestion
from app.schemas.typings.conversations.constrained_integers import (
    AnswersToImproveLimit,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.users.prefixed_id import UserId
from tests.brain.scripted_turns import say
from tests.teaching.correction_helpers import fix
from tests.teaching.teaching_world import TeachingWorld, build_teaching_world


def rate_bad(world: TeachingWorld, conversation_id: ConversationId) -> None:
    world.advance(60)
    world.rate.run(
        RateConversationCommand(
            user_id=world.brain.owner_id,
            business_id=world.brain.business.id,
            conversation_id=conversation_id,
            rating=ConversationRating.BAD,
            reason=ConversationRatingReason.WRONG_INFO,
        )
    )


def read(
    world: TeachingWorld, limit: int = 5, user_id: UserId | None = None
) -> AnswersToImproveView:
    return world.improve.run(
        AnswersToImproveQuery(
            user_id=user_id or world.brain.staff_id,
            business_id=world.brain.business.id,
            limit=AnswersToImproveLimit(limit),
        )
    )


def test_bad_ratings_come_first_then_open_questions() -> None:
    world = build_teaching_world(say("Не знаю."), say("Не уверен."))
    first = world.brain.send("Есть парковка?", user_id="nino")
    second = world.brain.send(
        "Можно с собакой?", channel=ChannelKind.TELEGRAM, user_id="tg-7", phone=None
    )
    rate_bad(world, first.conversation_id)
    rate_bad(world, second.conversation_id)
    world.record_question("Есть ли веганское меню?")
    world.record_question("Тест владельца", is_sandbox=True)

    view = read(world)

    assert [item.kind for item in view.items] == [
        AnswerToImproveKind.BAD_RATING,
        AnswerToImproveKind.BAD_RATING,
        AnswerToImproveKind.UNANSWERED_QUESTION,
    ]
    newest = view.items[0]
    assert newest.conversation_id == second.conversation_id
    assert newest.customer_message == "Можно с собакой?"
    assert newest.answer is not None and str(newest.answer).endswith("Не уверен.")
    assert newest.message_id == world.answer_of(second).id
    assert newest.rating_reason is ConversationRatingReason.WRONG_INFO
    assert view.items[2].question == "Есть ли веганское меню?"
    assert view.bad_rating_count == 2
    assert int(view.unanswered_count) >= 1


def test_the_limit_counts_both_kinds_together() -> None:
    world = build_teaching_world(say("Не знаю."))
    reply = world.brain.send("Есть парковка?")
    rate_bad(world, reply.conversation_id)
    world.record_question("Есть ли веганское меню?")

    view = read(world, limit=1)

    assert [item.kind for item in view.items] == [AnswerToImproveKind.BAD_RATING]
    assert view.bad_rating_count == 1


def test_a_corrected_answer_leaves_the_list() -> None:
    world = build_teaching_world(say("Не знаю."))
    reply = world.brain.send("Есть парковка?")
    rate_bad(world, reply.conversation_id)

    fix(
        world,
        world.answer_of(reply),
        AnswerCorrectionScope.FAQ,
        correct_answer="Да, во дворе.",
    )

    view = read(world)
    assert view.items == []
    assert view.bad_rating_count == 0


def test_a_check_saved_from_a_bad_rating_leaves_the_list() -> None:
    world = build_teaching_world(say("Не знаю."))
    reply = world.brain.send("Есть парковка?")
    rate_bad(world, reply.conversation_id)

    world.create_case.run(
        CreateAutotestCaseCommand(
            user_id=world.brain.owner_id,
            business_id=world.brain.business.id,
            case=AutotestCaseInput(
                question=AutotestCaseQuestion("Есть парковка?"),
                expectation=AutotestExpectation.MUST_HAND_OFF,
                source=AutotestCaseSource.BAD_RATING,
                source_conversation_id=reply.conversation_id,
                source_message_id=world.answer_of(reply).id,
            ),
        )
    )

    assert read(world).bad_rating_count == 0


def test_strangers_see_nothing() -> None:
    world = build_teaching_world()

    with pytest.raises(NotFoundError):
        read(world, user_id=UserId())
