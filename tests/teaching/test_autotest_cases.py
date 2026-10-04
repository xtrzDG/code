"""
"My checks": the owner writes, changes and removes checks; each keeps what
its expectation needs, a business keeps a few dozen, no two are the same,
and the list shows how each did in the latest run.
"""

import json
from typing import Any

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AutotestCaseSource,
    AutotestCheckCode,
    AutotestOutcome,
    AutotestScenarioKind,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import (
    AutotestRunDocument,
    AutotestScenarioResult,
    AutotestTranscriptLine,
    AutotestVerdict,
)
from app.schemas.dto.assistants.autotest_cases import (
    AutotestCaseChanges,
    AutotestCaseCommand,
    AutotestCaseInput,
    AutotestCaseList,
    AutotestCaseView,
    CreateAutotestCaseCommand,
    ListAutotestCasesQuery,
    UpdateAutotestCaseCommand,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.assistants.constrained_integers import AutotestScenarioCount
from app.schemas.typings.assistants.constrained_strings import AutotestScenarioKey
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import UnansweredQuestionId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.autotests.cases.autotest_case_rules import AUTOTEST_CASE_LIMIT
from tests.brain.scripted_turns import say
from tests.teaching.teaching_world import TeachingWorld, build_teaching_world

PARKING: dict[str, Any] = {
    "question": "Есть парковка?",
    "expectation": "must_mention",
    "expected_text": "во дворе",
}


def create(
    world: TeachingWorld, user_id: UserId | None = None, **fields: Any
) -> AutotestCaseView:
    world.advance(60)
    return world.create_case.run(
        CreateAutotestCaseCommand(
            user_id=user_id or world.brain.owner_id,
            business_id=world.brain.business.id,
            case=AutotestCaseInput.model_validate_json(json.dumps(fields)),
        )
    )


def update(
    world: TeachingWorld, case_id: AutotestCaseId, **fields: Any
) -> AutotestCaseView:
    world.advance(60)
    return world.update_case.run(
        UpdateAutotestCaseCommand(
            user_id=world.brain.owner_id,
            business_id=world.brain.business.id,
            case_id=case_id,
            changes=AutotestCaseChanges.model_validate_json(json.dumps(fields)),
        )
    )


def listed(world: TeachingWorld) -> AutotestCaseList:
    return world.list_cases.run(
        ListAutotestCasesQuery(
            user_id=world.brain.owner_id, business_id=world.brain.business.id
        )
    )


def test_a_check_takes_the_business_language_and_lists_in_order() -> None:
    world = build_teaching_world()

    first = create(world, **PARKING)
    second = create(
        world, question="Позовите менеджера", expectation="must_hand_off", language="en"
    )

    assert first.language == world.brain.business.default_language
    assert first.source is AutotestCaseSource.OWNER
    assert first.is_active is True
    assert first.last_result is None
    view = listed(world)
    assert [case.id for case in view.items] == [first.id, second.id]
    assert view.limit == AUTOTEST_CASE_LIMIT
    assert world.case_repo.list_by_business(world.brain.business.id)[0].created_by == (
        world.brain.owner_id
    )


def test_a_text_expectation_needs_its_text_and_others_drop_it() -> None:
    world = build_teaching_world()

    with pytest.raises(ValidationFailedError):
        create(world, question="Есть парковка?", expectation="must_not_mention")
    with pytest.raises(ValidationFailedError):
        create(world, **{**PARKING, "expected_text": "_"})
    lead = create(
        world,
        question="Хочу заказать банкет",
        expectation="must_create_lead",
        expected_text="банкет",
    )

    assert lead.expected_text is None


def test_the_same_check_twice_is_a_conflict() -> None:
    world = build_teaching_world()
    create(world, **PARKING)

    with pytest.raises(ConflictError):
        create(world, **{**PARKING, "question": "есть ПАРКОВКА"})
    create(world, **{**PARKING, "expectation": "must_not_mention"})


def test_a_business_keeps_at_most_the_limit() -> None:
    world = build_teaching_world()
    for index in range(int(AUTOTEST_CASE_LIMIT)):
        create(world, **{**PARKING, "question": f"Вопрос номер {index}"})

    with pytest.raises(ValidationFailedError):
        create(world, **PARKING)


def test_a_check_saved_from_a_conversation_names_records_of_the_business() -> None:
    world = build_teaching_world(say("Не знаю."), say("Тоже не знаю."))
    reply = world.brain.send("Есть парковка?")
    other = world.brain.send("А террасa?", user_id="tg-2", phone=None)
    question = world.record_question("Есть ли веганское меню?")

    saved = create(
        world,
        **PARKING,
        source="correction",
        source_conversation_id=str(reply.conversation_id),
        source_message_id=str(world.answer_of(reply).id),
    )
    from_question = create(
        world,
        question="Есть ли веганское меню?",
        expectation="must_hand_off",
        source="unanswered_question",
        source_question_id=str(question.id),
    )

    assert saved.source_conversation_id == reply.conversation_id
    assert from_question.source is AutotestCaseSource.UNANSWERED_QUESTION
    for wrong in (
        {"source_conversation_id": str(ConversationId())},
        {"source_message_id": str(MessageId())},
        {
            "source_conversation_id": str(reply.conversation_id),
            "source_message_id": str(world.answer_of(other).id),
        },
        {"source_question_id": str(UnansweredQuestionId())},
    ):
        with pytest.raises(NotFoundError):
            create(world, **{**PARKING, "question": "Другой вопрос", **wrong})


def test_changes_keep_the_rules_and_switch_a_check_off() -> None:
    world = build_teaching_world()
    case = create(world, **PARKING)
    other = create(world, **{**PARKING, "question": "Есть терраса?"})

    changed = update(world, case.id, expected_text="бесплатная", is_active=False)
    handoff = update(world, other.id, expectation="must_hand_off")

    assert changed.expected_text == "бесплатная"
    assert changed.is_active is False
    assert handoff.expected_text is None
    with pytest.raises(ConflictError):
        update(
            world,
            other.id,
            question=PARKING["question"],
            **{
                "expectation": "must_mention",
                "expected_text": "бесплатная",
            },
        )
    with pytest.raises(NotFoundError):
        update(world, AutotestCaseId(), is_active=True)


def test_a_check_is_removed_and_only_by_an_owner() -> None:
    world = build_teaching_world()
    case = create(world, **PARKING)
    command = AutotestCaseCommand(
        user_id=world.brain.owner_id,
        business_id=world.brain.business.id,
        case_id=case.id,
    )

    with pytest.raises(AccessDeniedError):
        world.delete_case.run(
            command.model_copy(update={"user_id": world.brain.staff_id})
        )
    with pytest.raises(AccessDeniedError):
        create(world, world.brain.staff_id, **PARKING)
    world.delete_case.run(command)

    assert listed(world).items == []
    with pytest.raises(NotFoundError):
        world.delete_case.run(command)


def test_the_list_shows_the_result_of_the_newest_run() -> None:
    world = build_teaching_world()
    case = create(world, **PARKING)
    version = world.brain.version
    run = AutotestRunDocument(
        business_id=world.brain.business.id,
        assistant_version_id=version.id,
        results=[
            AutotestScenarioResult(
                scenario_key=AutotestScenarioKey(f"owner_check__{case.id}"),
                kind=AutotestScenarioKind.OWNER_CHECK,
                language=case.language,
                outcome=AutotestOutcome.FAILED,
                check_codes=[AutotestCheckCode.EXPECTED_TEXT_MISSING],
                transcript=[
                    AutotestTranscriptLine(
                        author=MessageAuthor.CUSTOMER,
                        text=MessageText("Есть парковка?"),
                    ),
                    AutotestTranscriptLine(
                        author=MessageAuthor.ASSISTANT, text=MessageText("Не знаю.")
                    ),
                ],
                autotest_case_id=case.id,
            )
        ],
    )
    world.run_repo.save(run)
    world.brain.version_repo.save(
        version.model_copy(
            update={
                "autotest_verdict": AutotestVerdict(
                    run_id=run.id,
                    is_passed=False,
                    scenario_count=AutotestScenarioCount(1),
                    passed_count=AutotestScenarioCount(0),
                    finished_at=Microseconds(1_800_000_000_000_000),
                )
            }
        )
    )

    result = listed(world).items[0].last_result

    assert result is not None
    assert result.run_id == run.id
    assert result.outcome is AutotestOutcome.FAILED
    assert result.check_codes == [AutotestCheckCode.EXPECTED_TEXT_MISSING]
    assert result.answer == "Не знаю."
    assert result.assistant_version_number == version.version_number
