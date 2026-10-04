"""
The review side of conversations (the same collection as the feed's):
ratings with their reasons and the "Answers worth improving" they leave.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversation_feed.answer_reviews import ConversationRatingChange
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.platform.constrained_integers import ListItemCount


class ConversationReviewRepoContract(RepoContract, Protocol):
    def set_rating(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        change: ConversationRatingChange,
    ) -> ConversationDocument | None:
        """
        Store the rating, its reason and answer in one step, with
        `awaits_improvement` derived again; None when the conversation is
        missing.
        """
        raise NotImplementedError

    def mark_improved(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        at: Microseconds,
    ) -> ConversationDocument | None:
        """
        Someone corrected an answer of the conversation or saved a check from
        it: `improved_at`, so a bad rating no longer waits; None when the
        conversation is missing.
        """
        raise NotImplementedError

    def page_awaiting_improvement(
        self, business_id: BusinessId, window: KeysetSlice
    ) -> list[ConversationDocument]:
        """Rated bad and not acted on, the latest message first."""
        raise NotImplementedError

    def count_awaiting_improvement(self, business_id: BusinessId) -> ListItemCount:
        raise NotImplementedError
