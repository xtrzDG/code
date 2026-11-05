from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import (
    UnansweredQuestionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.dto.handoffs import (
    RecordUnansweredQuestionCommand,
    UnansweredQuestionView,
)
from app.schemas.typings.handoffs.constrained_integers import QuestionOccurrenceCount
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.use_cases.shared.business_access import require_business
from app.use_cases.shared.handoff_views import build_unanswered_question_view


class RecordUnansweredQuestionUseCase(
    UseCaseContract[RecordUnansweredQuestionCommand, UnansweredQuestionView]
):
    """
    Remember a customer question the knowledge base did not answer (concept:
    "questions without an answer" in the cabinet).

    An unresolved question with the same text (case and spacing ignored)
    counts one more occurrence instead of a duplicate. Sandbox questions
    (owner tests, autotests) are kept apart from real ones.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        unanswered_question_repo: UnansweredQuestionRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._unanswered_question_repo: UnansweredQuestionRepoContract = (
            unanswered_question_repo
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(
        self, input_data: RecordUnansweredQuestionCommand
    ) -> UnansweredQuestionView:
        require_business(self._business_repo, input_data.business_id)
        now: Microseconds = self._wall_clock.now_unix()
        question_key: str = normalize_question(input_data.question)
        for question in self._unanswered_question_repo.list_by_business(
            input_data.business_id
        ):
            if (
                not question.is_resolved
                and question.is_sandbox == input_data.is_sandbox
                and normalize_question(question.question) == question_key
            ):
                question.occurrence_count = QuestionOccurrenceCount(
                    int(question.occurrence_count) + 1
                )
                question.last_seen_at = now
                question.updated_at = now
                self._unanswered_question_repo.save(question)
                return build_unanswered_question_view(question)

        question = UnansweredQuestionDocument(
            business_id=input_data.business_id,
            question=input_data.question,
            language=input_data.language,
            last_seen_at=now,
            is_sandbox=input_data.is_sandbox,
            created_at=now,
            updated_at=now,
        )
        self._unanswered_question_repo.save(question)
        return build_unanswered_question_view(question)


def normalize_question(question: UnansweredQuestionText) -> str:
    """Comparison key: case-folded text with runs of whitespace collapsed."""

    return " ".join(str(question).casefold().split())
