"""
The review writes of `ConversationRepository`: a rating (with its reason
and answer) and the mark that someone acted on it are written in one step
each, and the conversations rated bad and not acted on are one keyset
page on their own index (migration 1112).
"""

from typed_time_provider import Microseconds

from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import LAST_MESSAGE_AT_FIELD
from app.repositories.document_queries import field_equals
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversation_feed.answer_reviews import ConversationRatingChange
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.utilities.conversations.review_fields import with_review_attention

AWAITS_IMPROVEMENT_FIELD: DocumentFieldPath = DocumentFieldPath("awaits_improvement")


class ConversationReviewWrites(BusinessScopedRepository[ConversationDocument]):
    """Ratings, their reasons and the answers worth improving."""

    def set_rating(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        change: ConversationRatingChange,
    ) -> ConversationDocument | None:
        is_rated: bool = change.rating is not None

        def rate(stored: ConversationDocument) -> ConversationDocument:
            return with_review_attention(
                stored.model_copy(
                    update={
                        "rating": change.rating,
                        "rated_by": change.rated_by if is_rated else None,
                        "rated_at": change.at if is_rated else None,
                        "rating_reason": change.rating_reason if is_rated else None,
                        "rated_message_id": (
                            change.rated_message_id if is_rated else None
                        ),
                        "updated_at": change.at,
                    }
                )
            )

        return self._modify_in_business(business_id, str(conversation_id), rate)

    def mark_improved(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        at: Microseconds,
    ) -> ConversationDocument | None:
        def mark(stored: ConversationDocument) -> ConversationDocument:
            return with_review_attention(
                stored.model_copy(update={"improved_at": at, "updated_at": at})
            )

        return self._modify_in_business(business_id, str(conversation_id), mark)

    def page_awaiting_improvement(
        self, business_id: BusinessId, window: KeysetSlice
    ) -> list[ConversationDocument]:
        return self._page_in_business(
            business_id,
            (LAST_MESSAGE_AT_FIELD,),
            window,
            DocumentFilter(matches=(field_equals(AWAITS_IMPROVEMENT_FIELD, True),)),
        )

    def count_awaiting_improvement(self, business_id: BusinessId) -> ListItemCount:
        return ListItemCount(
            int(
                self._count_in_business(
                    business_id, (field_equals(AWAITS_IMPROVEMENT_FIELD, True),)
                )
            )
        )
