from app.contracts.repositories.booking_repositories import (
    UnansweredQuestionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.dto.operations.unanswered_questions import (
    ListUnansweredQuestionsQuery,
    UnansweredQuestionPage,
)
from app.schemas.dto.paging import KeysetPosition
from app.schemas.typings.platform.integers import ListSortValue
from app.schemas.typings.platform.strings import ListItemKey
from app.use_cases.handoffs.handoff_views import build_unanswered_question_details
from app.utilities.paging.keyset_paging import finish_page, read_slice

# The occurrence count sits above every possible timestamp (64 bits), so one
# integer key orders by count first and by the last time asked second.
OCCURRENCE_RANK_SHIFT: int = 64
LAST_SEEN_MASK: int = (1 << OCCURRENCE_RANK_SHIFT) - 1


class ListUnansweredQuestionsUseCase(
    UseCaseContract[ListUnansweredQuestionsQuery, UnansweredQuestionPage]
):
    """
    Questions without an answer for the cabinet, one page at a time: open
    ones by default, most asked first, then the most recently asked (ties
    in write order). The resolved and sandbox filters apply before paging;
    pages are keyset pages read by the database.
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
        page_items, next_cursor = finish_page(
            self._unanswered_question_repo.page_by_rank(
                input_data.business_id,
                read_slice(input_data.page, rank_position),
                input_data.include_resolved,
                input_data.include_sandbox,
            ),
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


def rank_position(rank: int, item_id: str) -> KeysetPosition:
    """The (occurrence count, last asked) position a cursor's key stands for."""

    return KeysetPosition(
        sort_values=(
            ListSortValue(rank >> OCCURRENCE_RANK_SHIFT),
            ListSortValue(rank & LAST_SEEN_MASK),
        ),
        item_key=ListItemKey(item_id),
    )
