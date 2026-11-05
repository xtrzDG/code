"""
"Fix this answer" at its edges: an answer that opened the conversation,
an answer of another conversation, lookups that name no item, and a
correction whose answer is only spaces.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.knowledge import AnswerCorrectionScope
from app.schemas.domain.conversations import MessageDocument, ToolCallRecord
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
)
from tests.brain.scripted_turns import say
from tests.teaching.correction_helpers import fix, open_draft
from tests.teaching.teaching_world import TeachingWorld, build_teaching_world

PARKING: str = "Есть ли у вас парковка?"
ONE_HOUR_US: int = 3_600_000_000


def stored_copy(
    world: TeachingWorld, answer: MessageDocument, **changes: object
) -> MessageDocument:
    """Another answer of the same conversation, an hour before the first one."""

    copy = answer.model_copy(
        update={
            "id": MessageId(),
            "created_at": Microseconds(int(answer.created_at) - ONE_HOUR_US),
            **changes,
        }
    )
    world.brain.message_repo.save(copy)
    return copy


def test_an_answer_that_opened_the_conversation_has_no_question() -> None:
    world = build_teaching_world(say("Нет."))
    answer = world.answer_of(world.brain.send(PARKING))
    greeting = stored_copy(world, answer)

    draft = open_draft(world, greeting)

    assert draft.question is None
    assert draft.current_fact is None


def test_an_answer_of_another_conversation_is_not_found() -> None:
    world = build_teaching_world(say("Нет."), say("Тоже нет."))
    first = world.answer_of(world.brain.send(PARKING))
    second = world.answer_of(world.brain.send("А терраса?", user_id="tg-2", phone=None))
    assert first.conversation_id != second.conversation_id

    with pytest.raises(NotFoundError):
        open_draft(
            world, first.model_copy(update={"conversation_id": second.conversation_id})
        )


def test_lookups_that_name_no_item_leave_no_current_fact() -> None:
    world = build_teaching_world(say("Нет."))
    answer = world.answer_of(world.brain.send(PARKING))
    lookup = stored_copy(
        world,
        answer,
        tool_calls=[
            ToolCallRecord(
                tool_name=AssistantToolName.SEARCH_KNOWLEDGE,
                input_json=LlmToolInputJson('{"query":"парковка"}'),
                result_json=LlmToolResultJson('{"matches":[{"id":"not-an-item-id"}]}'),
            )
        ],
    )

    draft = open_draft(world, lookup)

    assert draft.current_fact is None


def test_an_answer_of_only_spaces_is_refused() -> None:
    world = build_teaching_world(say("Нет."))
    answer = world.answer_of(world.brain.send(PARKING))

    with pytest.raises(ValidationFailedError):
        fix(world, answer, AnswerCorrectionScope.FAQ, correct_answer="   ")
