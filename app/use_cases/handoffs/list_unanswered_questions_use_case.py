from app.contracts.repositories import UnansweredQuestionRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.dto.operations import (
    ListUnansweredQuestionsQuery,
    UnansweredQuestionPage,
)
from app.use_cases.handoffs.handoff_views import build_unanswered_question_details
from app.utilities.paging.cursor_paging import take_page

# The occurrence count sits above every possible timestamp (64 bits), so one
# integer key orders by count first and by the last time asked second.
OCCURRENCE_RANK_SHIFT: int = 64


class ListUnansweredQuestionsUseCase(
    UseCaseContract[ListUnansweredQuestionsQuery, UnansweredQuestionPage]
):
    """
    Questions without an answer for the cabinet, one page at a time: open
    ones by default, most asked first, then the most recently asked (ties
    by id). The resolved and sandbox filters apply before paging.
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
    ) -> UnansweredQuestionPage:
        questions: list[UnansweredQuestionDocument] = [
            question
            for question in self._unanswered_question_repo.list_by_business(
                input_data.business_id
            )
            if (input_data.include_resolved or not question.is_resolved)
            and (input_data.include_sandbox or not question.is_sandbox)
        ]
        page_items, next_cursor = take_page(
            questions,
            input_data.page,
            sort_key=rank_question,
            item_id=lambda question: str(question.id),
        )
        return UnansweredQuestionPage(
            items=[
                build_unanswered_question_details(question) for question in page_items
            ],
            next_cursor=next_cursor,
        )


def rank_question(question: UnansweredQuestionDocument) -> int:
    """Paging key: occurrence count first, then the last time it was asked."""

    return (int(question.occurrence_count) << OCCURRENCE_RANK_SHIFT) + int(
        question.last_seen_at
    )
