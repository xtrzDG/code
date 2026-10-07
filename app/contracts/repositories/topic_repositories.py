"""
Persistence contracts of what customers ask about: the topics document of
each business, and the reads its nightly grouping needs (the conversations
customers started and the first message of each). Every read is limited
to one business; sandbox conversations are left out.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.conversation_topics import ConversationTopicsDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit


class ConversationTopicsRepoContract(RepoContract, Protocol):
    def get(self, business_id: BusinessId) -> ConversationTopicsDocument | None:
        """The business's topics as last grouped; None: never grouped yet."""
        raise NotImplementedError

    def save(self, topics: ConversationTopicsDocument) -> None:
        raise NotImplementedError


class TopicInputRepoContract(RepoContract, Protocol):
    def list_started(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
        limit: DocumentQueryLimit,
    ) -> list[ConversationDocument]:
        """The newest conversations started from `start` to `end`, newest first."""
        raise NotImplementedError

    def find_first_customer_message(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> MessageDocument | None:
        """The first message the customer wrote in the conversation."""
        raise NotImplementedError
