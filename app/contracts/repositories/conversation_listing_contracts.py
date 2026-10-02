"""
Keyset pages and database counts of contacts, conversations, messages,
calls and the audit log (the feed, the conversation card, the dashboard,
the admin page, the audit page).
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    MessageDocument,
)
from app.schemas.dto.conversation_feed.message_tallies import (
    ConversationMessageTally,
    ConversationUsageView,
)
from app.schemas.dto.listing_filters import AuditLogFilter, ConversationFeedFilter
from app.schemas.dto.operations.activity_counts import (
    ActivityPeriod,
    ConversationMixCount,
    ConversationTimelineCount,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.users.prefixed_id import UserId


class ContactListingContract(Protocol):
    def get_many(
        self, business_id: BusinessId, contact_ids: Sequence[ContactId]
    ) -> dict[ContactId, ContactDocument]:
        """The business's contacts of these ids in one read."""
        raise NotImplementedError


class ConversationListingContract(Protocol):
    def page_feed(
        self, business_id: BusinessId, window: KeysetSlice, feed: ConversationFeedFilter
    ) -> list[ConversationDocument]:
        """The latest message first, ties in write order."""
        raise NotImplementedError

    def count_started_by_mix(
        self, business_id: BusinessId, start: Microseconds, end: Microseconds
    ) -> list[ConversationMixCount]:
        """Started in the period per channel and language, no sandbox."""
        raise NotImplementedError

    def count_started_by_timeline(
        self, business_id: BusinessId, period: ActivityPeriod
    ) -> list[ConversationTimelineCount]:
        """Started per segment and after-hours flag, no sandbox."""
        raise NotImplementedError

    def list_sandbox_active_since(
        self, business_id: BusinessId, since: Microseconds
    ) -> list[ConversationId]:
        raise NotImplementedError


class MessageListingContract(Protocol):
    def page_transcript(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        window: KeysetSlice,
    ) -> list[MessageDocument]:
        """The conversation's messages newest first, ties in write order."""
        raise NotImplementedError

    def list_by_conversations(
        self, business_id: BusinessId, conversation_ids: Sequence[ConversationId]
    ) -> list[MessageDocument]:
        """Every message of these conversations, oldest first (search)."""
        raise NotImplementedError

    def tally_conversations(
        self, business_id: BusinessId, conversation_ids: Sequence[ConversationId]
    ) -> dict[ConversationId, ConversationMessageTally]:
        raise NotImplementedError

    def find_latest_written(
        self, business_id: BusinessId, conversation_id: ConversationId
    ) -> MessageDocument | None:
        """The newest message of the customer, the assistant or staff."""
        raise NotImplementedError

    def sum_usage(
        self, business_id: BusinessId, conversation_id: ConversationId
    ) -> ConversationUsageView:
        raise NotImplementedError

    def count_customer_messages(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
        conversation_ids: Sequence[ConversationId] | None = None,
    ) -> PeriodItemCount:
        raise NotImplementedError

    def sum_cost_by_conversation(
        self, business_id: BusinessId, start: Microseconds, end: Microseconds
    ) -> dict[ConversationId, CostMicroUsd]:
        raise NotImplementedError

    def list_with_tool_errors(
        self, business_id: BusinessId, since: Microseconds
    ) -> list[MessageDocument]:
        raise NotImplementedError


class CallListingContract(Protocol):
    def list_by_conversation(
        self, business_id: BusinessId, conversation_id: ConversationId
    ) -> list[CallDocument]:
        """The conversation's calls, the earliest first."""
        raise NotImplementedError


class AuditLogListingContract(Protocol):
    def page_by_business(
        self, business_id: BusinessId, window: KeysetSlice, log_filter: AuditLogFilter
    ) -> list[AuditLogEntryDocument]:
        """Newest first, ties in write order."""
        raise NotImplementedError

    def list_entities(self, business_id: BusinessId) -> list[AuditEntityName]:
        raise NotImplementedError

    def list_actors(self, business_id: BusinessId) -> list[UserId]:
        """Every person in the log, the most recent first."""
        raise NotImplementedError
