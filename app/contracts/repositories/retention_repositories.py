"""
Persistence contracts of the retention engine (migration 1123): each
business's privacy settings and purge state, and the indexed reads and
batched deletes the purge runs over records that went past retention.
"""

from collections.abc import Callable
from typing import Protocol

from base_pydantic_schemas import PersistentDocument
from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.retention_purges import RetentionPurgeStateDocument
from app.schemas.dto.retention import RetentionWindow
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.privacy.constrained_integers import RetentionBatchSize
from app.schemas.typings.storage.constrained_integers import DocumentCount


class BusinessPrivacySettingsRepoContract(RepoContract, Protocol):
    def get_or_default(
        self, business_id: BusinessId
    ) -> BusinessPrivacySettingsDocument:
        """The stored settings, or the defaults of a business without any."""
        raise NotImplementedError

    def save(self, settings: BusinessPrivacySettingsDocument) -> None:
        raise NotImplementedError


class RetentionPurgeStateRepoContract(RepoContract, Protocol):
    def get_or_new(self, business_id: BusinessId) -> RetentionPurgeStateDocument:
        """The stored state, or the state of a business never purged yet."""
        raise NotImplementedError

    def save(self, state: RetentionPurgeStateDocument) -> None:
        raise NotImplementedError


class QuietConversationRepoContract(RepoContract, Protocol):
    def page_quiet_in(
        self,
        business_id: BusinessId,
        window: RetentionWindow,
        after: ConversationDocument | None,
        size: RetentionBatchSize,
    ) -> list[ConversationDocument]:
        """
        The business's conversations whose last message lies in `window`,
        the quietest first, after `after` (one keyset batch on the
        `last_message_at` index).
        """
        raise NotImplementedError


class ExpiredMessageRepoContract(RepoContract, Protocol):
    def delete_created_before(
        self, business_id: BusinessId, cutoff: Microseconds
    ) -> DocumentCount:
        """Delete the business's messages written before `cutoff`; how many."""
        raise NotImplementedError


class ExpiredLlmTurnRepoContract(RepoContract, Protocol):
    def delete_by_conversation(self, conversation_id: ConversationId) -> DocumentCount:
        """Delete a conversation's model transcript; how many turns it had."""
        raise NotImplementedError


class ExpiredMissedCallRepoContract(RepoContract, Protocol):
    def delete_created_before(
        self, business_id: BusinessId, cutoff: Microseconds
    ) -> DocumentCount:
        """Delete the business's missed calls noted before `cutoff`; how many."""
        raise NotImplementedError


class ExpiringRecordRepoContract[Record: PersistentDocument](RepoContract, Protocol):
    """
    The business records a purge anonymizes (leads and handoffs by when
    they were made, bookings by when the visit ended): one keyset batch of
    those in a window at a time, each changed in one atomic step.
    """

    def page_in(
        self,
        business_id: BusinessId,
        window: RetentionWindow,
        after: Record | None,
        size: RetentionBatchSize,
    ) -> list[Record]:
        raise NotImplementedError

    def change(
        self,
        record: Record,
        change: Callable[[Record], Record | None],
    ) -> Record | None:
        """
        Store what `change` makes of the record as stored now; None, and
        nothing written, when it is gone or `change` returns None.
        """
        raise NotImplementedError
