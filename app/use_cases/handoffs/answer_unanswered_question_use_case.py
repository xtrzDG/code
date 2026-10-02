from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import (
    UnansweredQuestionRepoContract,
)
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.operations.unanswered_questions import (
    AnsweredQuestionResult,
    AnswerUnansweredQuestionCommand,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.use_cases.handoffs.handoff_views import build_unanswered_question_details


class AnswerUnansweredQuestionUseCase(
    UseCaseContract[AnswerUnansweredQuestionCommand, AnsweredQuestionResult]
):
    """
    "Add answer" in the cabinet (owner only): the answer becomes an active FAQ
    item in the question's language, sourced from the unanswered question,
    and the question is marked resolved with a link to it.

    Customers see the answer only after the assistant is reassembled and
    autotested, so the result asks for reassembly.
    """

    def __init__(
        self,
        unanswered_question_repo: UnansweredQuestionRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._unanswered_question_repo: UnansweredQuestionRepoContract = (
            unanswered_question_repo
        )
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(
        self, input_data: AnswerUnansweredQuestionCommand
    ) -> AnsweredQuestionResult:
        question: UnansweredQuestionDocument | None = (
            self._unanswered_question_repo.get(
                input_data.business_id, input_data.question_id
            )
        )
        if question is None:
            raise NotFoundError(f"Question {input_data.question_id} was not found.")

        if question.is_resolved:
            raise ConflictError("This question already has an answer.")

        now: Microseconds = self._wall_clock.now_unix()
        item = KnowledgeItemDocument(
            business_id=question.business_id,
            kind=KnowledgeItemKind.FAQ,
            title=input_data.title or KnowledgeTitle(str(question.question)),
            body=input_data.answer,
            languages=[question.language],
            source=KnowledgeItemSource.UNANSWERED_QUESTION,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._knowledge_item_repo.save(item)
        question.is_resolved = True
        question.resolved_knowledge_item_id = item.id
        question.updated_at = now
        self._unanswered_question_repo.save(question)
        return AnsweredQuestionResult(
            question=build_unanswered_question_details(question),
            knowledge_item_id=item.id,
            requires_reassembly=True,
        )
