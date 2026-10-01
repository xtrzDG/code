from app.contracts.repositories import UnansweredQuestionRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.dto.operations import (
    ListUnansweredQuestionsQuery,
    UnansweredQuestionListView,
)
from app.use_cases.handoffs.handoff_views import build_unanswered_question_details


class ListUnansweredQuestionsUseCase(
    UseCaseContract[ListUnansweredQuestionsQuery, UnansweredQuestionListView]
):
    """
    Questions without an answer for the cabinet: open ones by default, most
    asked first, then the most recently asked.
    """

    def __init__(
        self, unanswered_question_repo: UnansweredQuestionRepoContract
    ) -> None:
        self._unanswered_question_repo: UnansweredQuestionRepoContract = (
            unanswered_question_repo
        )

    def run(
        self,
        input_data: ListUnansweredQuestionsQuery,
    ) -> UnansweredQuestionListView:
        questions: list[UnansweredQuestionDocument] = [
            question
            for question in self._unanswered_question_repo.list_by_business(
                input_data.business_id
            )
            if (input_data.include_resolved or not question.is_resolved)
            and (input_data.include_sandbox or not question.is_sandbox)
        ]
        questions.sort(
            key=lambda question: (
                -int(question.occurrence_count),
                -int(question.last_seen_at),
            )
        )
        return UnansweredQuestionListView(
            items=[
                build_unanswered_question_details(question) for question in questions
            ]
        )
