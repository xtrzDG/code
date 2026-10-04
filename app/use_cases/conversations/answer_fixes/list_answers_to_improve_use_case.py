from app.contracts.repositories.booking_repositories import (
    UnansweredQuestionRepoContract,
)
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.repositories.conversation_review_contracts import (
    ConversationReviewRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.conversations import AnswerToImproveKind, MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.answers_to_improve import (
    AnswersToImproveQuery,
    AnswersToImproveView,
    AnswerToImproveView,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.handoffs.booleans import IsResolvedIncluded
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.utilities.conversations.message_previews import build_written_message_preview


class ListAnswersToImproveUseCase(
    UseCaseContract[AnswersToImproveQuery, AnswersToImproveView]
):
    """
    The Overview's "Answers worth improving", for owners and staff: the
    conversations rated bad that nobody acted on yet (newest first, with the
    rated answer and the customer's last words), then the questions the
    assistant could not answer (most asked first), `limit` together; and
    how many of each wait. Every read is one indexed query: a keyset page of
    each list, the rated answers by id and the customers' latest messages
    per conversation.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_review_repo: ConversationReviewRepoContract,
        message_repo: MessageRepoContract,
        unanswered_question_repo: UnansweredQuestionRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_review_repo: ConversationReviewRepoContract = (
            conversation_review_repo
        )
        self._message_repo: MessageRepoContract = message_repo
        self._unanswered_question_repo: UnansweredQuestionRepoContract = (
            unanswered_question_repo
        )

    def run(self, input_data: AnswersToImproveQuery) -> AnswersToImproveView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        limit: int = int(input_data.limit)
        rated: list[ConversationDocument] = (
            self._conversation_review_repo.page_awaiting_improvement(
                business.id, KeysetSlice(limit=KeysetReadLimit(limit))
            )
        )
        items: list[AnswerToImproveView] = self._bad_ratings(business, rated)
        if len(items) < limit:
            questions: list[UnansweredQuestionDocument] = (
                self._unanswered_question_repo.page_by_rank(
                    business.id,
                    KeysetSlice(limit=KeysetReadLimit(limit - len(items))),
                    IsResolvedIncluded(False),
                    IsSandboxIncluded(False),
                )
            )
            items.extend(to_question_item(question) for question in questions)

        return AnswersToImproveView(
            items=items,
            bad_rating_count=self._conversation_review_repo.count_awaiting_improvement(
                business.id
            ),
            unanswered_count=self._unanswered_question_repo.count_open(business.id),
        )

    def _bad_ratings(
        self, business: BusinessDocument, rated: list[ConversationDocument]
    ) -> list[AnswerToImproveView]:
        if not rated:
            return []

        conversation_ids: list[ConversationId] = [item.id for item in rated]
        answers: dict[MessageId, MessageDocument] = self._message_repo.get_many(
            business.id,
            [item.rated_message_id for item in rated if item.rated_message_id],
        )
        customer_lines: dict[ConversationId, MessageDocument] = (
            self._message_repo.find_latest_by_author(
                business.id, conversation_ids, MessageAuthor.CUSTOMER
            )
        )
        items: list[AnswerToImproveView] = []
        for conversation in rated:
            answer: MessageDocument | None = (
                None
                if conversation.rated_message_id is None
                else answers.get(conversation.rated_message_id)
            )
            customer: MessageDocument | None = customer_lines.get(conversation.id)
            items.append(
                AnswerToImproveView(
                    kind=AnswerToImproveKind.BAD_RATING,
                    conversation_id=conversation.id,
                    message_id=None if answer is None else answer.id,
                    customer_message=(
                        None
                        if customer is None
                        else build_written_message_preview(customer)
                    ),
                    answer=(
                        None
                        if answer is None
                        else build_written_message_preview(answer)
                    ),
                    rating_reason=conversation.rating_reason,
                    language=conversation.language,
                    at=conversation.rated_at or conversation.last_message_at,
                )
            )

        return items


def to_question_item(question: UnansweredQuestionDocument) -> AnswerToImproveView:
    return AnswerToImproveView(
        kind=AnswerToImproveKind.UNANSWERED_QUESTION,
        question_id=question.id,
        question=question.question,
        occurrence_count=question.occurrence_count,
        language=question.language,
        at=question.last_seen_at,
    )
