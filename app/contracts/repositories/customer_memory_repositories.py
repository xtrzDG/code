"""
Customer memory: how the assistant of a business treats returning
customers (Settings → General), and the conversations it remembers them
by (the same collection as the feed's; a customer's latest conversations
and their summaries).
"""

from collections.abc import Callable
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.customer_memory.conversation_summaries import (
    ConversationSummaryWrite,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit


class AssistantSettingsRepoContract(RepoContract, Protocol):
    def get_by_business(
        self, business_id: BusinessId
    ) -> AssistantSettingsDocument | None:
        """None: the business never changed them (the defaults apply)."""
        raise NotImplementedError

    def change(
        self,
        business_id: BusinessId,
        apply: Callable[[AssistantSettingsDocument], None],
        now: Microseconds,
    ) -> AssistantSettingsDocument:
        """
        Change the settings of a business as stored now, in one step
        (default settings are created first when there are none).
        """
        raise NotImplementedError


class ConversationMemoryRepoContract(RepoContract, Protocol):
    def list_latest_by_contact(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
        limit: DocumentQueryLimit,
    ) -> list[ConversationDocument]:
        """A customer's conversations, the latest message first (indexed)."""
        raise NotImplementedError

    def count_by_contact(
        self, business_id: BusinessId, contact_id: ContactId
    ) -> ListItemCount:
        """How many real (not sandbox) conversations a customer had."""
        raise NotImplementedError

    def set_summary(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        write: ConversationSummaryWrite,
    ) -> ConversationDocument | None:
        """
        Store the summary in one step, only while the conversation is as
        summarized: None, and nothing written, when it is missing, got a
        message after `write.covers_until`, or its visitor was erased
        meanwhile.
        """
        raise NotImplementedError
