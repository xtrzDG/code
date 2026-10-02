from datetime import datetime

import pytest

from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.dto.handoffs import (
    RecordUnansweredQuestionCommand,
    UnansweredQuestionView,
)
from app.schemas.dto.operations.unanswered_questions import (
    AnswerUnansweredQuestionCommand,
    ListUnansweredQuestionsQuery,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.prefixed_id import UnansweredQuestionId
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_integers import PageSize
from tests.operations.builders import OperationsWorld


class QuestionsFixture:
    def __init__(self) -> None:
        self.world = OperationsWorld()
        self.business = self.world.add_business()

    def record(
        self,
        text: str,
        language: str = "ru",
        is_sandbox: bool = False,
        business_id: BusinessId | None = None,
    ) -> UnansweredQuestionView:
        return self.world.record_unanswered_question().run(
            RecordUnansweredQuestionCommand(
                business_id=business_id or self.business.id,
                question=UnansweredQuestionText(text),
                language=LanguageTag(language),
                is_sandbox=is_sandbox,
            )
        )


def test_same_question_is_counted_once_ignoring_case_and_spacing() -> None:
    questions = QuestionsFixture()

    first = questions.record("Есть ли   парковка?")
    questions.world.clock.move_to(datetime.fromisoformat("2026-10-05T09:00:00+00:00"))
    second = questions.record("есть ли парковка?")
    sandbox = questions.record("Есть ли парковка?", is_sandbox=True)

    assert second.id == first.id
    assert sandbox.id != first.id
    stored = questions.world.question_repo.get(questions.business.id, first.id)
    assert stored is not None
    assert stored.occurrence_count == 2
    assert stored.last_seen_at == questions.world.clock.now_microseconds()
    assert stored.question == "Есть ли   парковка?"


def test_list_orders_by_frequency_and_hides_sandbox_and_resolved() -> None:
    questions = QuestionsFixture()
    questions.record("Do you have vegan khinkali?", language="en")
    parking = questions.record("პარკინგი გაქვთ?", language="ka")
    questions.record("პარკინგი  გაქვთ?", language="ka")
    questions.record("Is there Wi-Fi?", language="en", is_sandbox=True)

    listed = questions.world.list_unanswered_questions().run(
        ListUnansweredQuestionsQuery(business_id=questions.business.id)
    )
    everything = questions.world.list_unanswered_questions().run(
        ListUnansweredQuestionsQuery(
            business_id=questions.business.id,
            include_resolved=True,
            include_sandbox=True,
        )
    )

    assert [item.id for item in listed.items][0] == parking.id
    assert [item.occurrence_count for item in listed.items] == [2, 1]
    assert len(everything.items) == 3


def test_list_pages_most_asked_first_then_most_recent() -> None:
    questions = QuestionsFixture()
    clock = questions.world.clock
    clock.move_to(datetime.fromisoformat("2026-10-02T09:00:00+00:00"))
    older = questions.record("Do you deliver?", language="en")
    clock.move_to(datetime.fromisoformat("2026-10-03T09:00:00+00:00"))
    newer = questions.record("Is there a terrace?", language="en")
    clock.move_to(datetime.fromisoformat("2026-10-04T09:00:00+00:00"))
    frequent = questions.record("Can I bring a dog?", language="en")
    questions.record("can i bring a dog?", language="en")
    list_questions = questions.world.list_unanswered_questions()

    first = list_questions.run(
        ListUnansweredQuestionsQuery(
            business_id=questions.business.id,
            page=PageRequest(size=PageSize(2)),
        )
    )
    assert first.next_cursor is not None
    second = list_questions.run(
        ListUnansweredQuestionsQuery(
            business_id=questions.business.id,
            page=PageRequest(size=PageSize(2), cursor=first.next_cursor),
        )
    )

    assert [item.id for item in first.items] == [frequent.id, newer.id]
    assert [item.id for item in second.items] == [older.id]
    assert second.next_cursor is None


def test_answer_becomes_an_active_faq_and_asks_for_reassembly() -> None:
    questions = QuestionsFixture()
    parking = questions.record("Есть ли парковка?")

    result = questions.world.answer_unanswered_question().run(
        AnswerUnansweredQuestionCommand(
            business_id=questions.business.id,
            question_id=parking.id,
            answer=KnowledgeBody("Да, бесплатная, во дворе."),
        )
    )

    assert result.requires_reassembly
    assert result.question.is_resolved
    assert result.question.resolved_knowledge_item_id == result.knowledge_item_id
    item = questions.world.knowledge_repo.get(
        questions.business.id, result.knowledge_item_id
    )
    assert item is not None
    assert (item.kind, item.source, item.is_active) == (
        KnowledgeItemKind.FAQ,
        KnowledgeItemSource.UNANSWERED_QUESTION,
        True,
    )
    assert (item.title, item.body, item.languages) == (
        "Есть ли парковка?",
        "Да, бесплатная, во дворе.",
        ["ru"],
    )
    # A resolved question is asked again: it starts a new open question.
    assert questions.record("Есть ли парковка?").id != parking.id
    with pytest.raises(ConflictError):
        questions.world.answer_unanswered_question().run(
            AnswerUnansweredQuestionCommand(
                business_id=questions.business.id,
                question_id=parking.id,
                answer=KnowledgeBody("Again"),
                title=KnowledgeTitle("Parking"),
            )
        )


def test_unknown_question_or_business() -> None:
    questions = QuestionsFixture()

    with pytest.raises(NotFoundError):
        questions.world.answer_unanswered_question().run(
            AnswerUnansweredQuestionCommand(
                business_id=questions.business.id,
                question_id=UnansweredQuestionId(),
                answer=KnowledgeBody("Yes"),
            )
        )

    with pytest.raises(NotFoundError):
        questions.record("Hello?", business_id=BusinessId())


def test_custom_title_is_used_for_the_faq() -> None:
    questions = QuestionsFixture()
    wifi = questions.record("wifi pass??", language="en")

    result = questions.world.answer_unanswered_question().run(
        AnswerUnansweredQuestionCommand(
            business_id=questions.business.id,
            question_id=wifi.id,
            answer=KnowledgeBody("Ask the waiter for today's password."),
            title=KnowledgeTitle("Wi-Fi password"),
        )
    )

    item = questions.world.knowledge_repo.get(
        questions.business.id, result.knowledge_item_id
    )
    assert item is not None and item.title == "Wi-Fi password"
