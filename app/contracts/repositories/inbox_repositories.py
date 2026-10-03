"""
Persistence contracts of the team inbox: the team fields of conversations
(assignment, open requests) and the inbox views over them, the open work
of a page of conversations, internal notes, saved replies and the inbox
settings.

Implementations return independent copies: mutating a returned document
does not change stored state until it is saved. Every document is looked
up through its business id, so one tenant never sees another's data.
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.inbox_settings import InboxSettingsDocument
from app.schemas.domain.quick_replies import QuickReplyLibraryDocument
from app.schemas.dto.inbox.assignment import ConversationAssignmentChange
from app.schemas.dto.inbox.inbox_views import InboxViewCounts, InboxViewFilter
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.inbox.booleans import HasOpenRequest
from app.schemas.typings.inbox.constrained_integers import (
    AwaitingConversationCount,
    ConversationNoteCount,
)
from app.schemas.typings.inbox.prefixed_id import ConversationNoteId
from app.schemas.typings.users.prefixed_id import UserId


class ConversationTeamRepoContract(RepoContract, Protocol):
    """The team side of conversations (the same collection as the feed's)."""

    def get(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> ConversationDocument | None:
        raise NotImplementedError

    def assign(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        change: ConversationAssignmentChange,
    ) -> ConversationDocument | None:
        """
        Compare and set, in one step: when the stored `assignment_revision`
        is `change.expected_revision`, write the new assignee, who assigned
        it and when, and the next revision. None, and nothing written, when
        the conversation is missing or its revision moved on.
        """
        raise NotImplementedError

    def set_open_request(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        has_open_request: HasOpenRequest,
        at: Microseconds,
    ) -> ConversationDocument | None:
        """
        Store whether the conversation has an open request (and so whether
        it waits for the team); None when the conversation is missing.
        """
        raise NotImplementedError

    def page_inbox(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        view: InboxViewFilter,
    ) -> list[ConversationDocument]:
        """
        One keyset page of a view (sandbox left out), the latest message
        first, ties in write order: NEEDS_PERSON in HANDOFF, REQUESTS with
        an open request, MINE waiting for the team and assigned to the
        viewer, UNASSIGNED waiting for the team with nobody assigned, ALL.
        """
        raise NotImplementedError

    def count_inbox(self, business_id: BusinessId, viewer: UserId) -> InboxViewCounts:
        """The counts of the views as `viewer` sees them (one grouped count)."""
        raise NotImplementedError

    def count_awaiting_by_assignee(
        self, business_id: BusinessId
    ) -> dict[UserId, AwaitingConversationCount]:
        """How many conversations waiting for the team each member has."""
        raise NotImplementedError


class InboxWorkRepoContract(RepoContract, Protocol):
    """The open handoffs and requests behind the conversations of the inbox."""

    def latest_open_handoffs(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
    ) -> dict[ConversationId, HandoffDocument]:
        """The newest unresolved handoff of each conversation that has one."""
        raise NotImplementedError

    def latest_open_requests(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
    ) -> dict[ConversationId, LeadDocument]:
        """The newest new or in-progress request of each conversation."""
        raise NotImplementedError

    def has_open_request(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> HasOpenRequest:
        """Whether a request of the conversation is new or in progress."""
        raise NotImplementedError


class ConversationNoteRepoContract(RepoContract, Protocol):
    def add(self, note: ConversationNoteDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        note_id: ConversationNoteId,
    ) -> ConversationNoteDocument | None:
        raise NotImplementedError

    def page_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        window: KeysetSlice,
    ) -> list[ConversationNoteDocument]:
        """One keyset page of a conversation's notes, newest first."""
        raise NotImplementedError

    def list_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> list[ConversationNoteDocument]:
        """Every note of a conversation, oldest first (data export)."""
        raise NotImplementedError

    def count_by_conversations(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
    ) -> dict[ConversationId, ConversationNoteCount]:
        """How many notes each conversation has (one grouped count)."""
        raise NotImplementedError

    def delete(self, business_id: BusinessId, note_id: ConversationNoteId) -> None:
        raise NotImplementedError

    def delete_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> ConversationNoteCount:
        """Delete every note of a conversation (data erasure); how many."""
        raise NotImplementedError


class QuickReplyLibraryRepoContract(RepoContract, Protocol):
    def get_by_business(
        self, business_id: BusinessId
    ) -> QuickReplyLibraryDocument | None:
        raise NotImplementedError

    def change(
        self,
        business_id: BusinessId,
        apply: Callable[[QuickReplyLibraryDocument], None],
        now: Microseconds,
    ) -> QuickReplyLibraryDocument:
        """
        Change the saved replies of a business as stored now, in one step
        (an empty library is created first when there is none). An error
        raised by `apply` leaves the library as it was.
        """
        raise NotImplementedError


class InboxSettingsRepoContract(RepoContract, Protocol):
    def get_by_business(self, business_id: BusinessId) -> InboxSettingsDocument | None:
        raise NotImplementedError

    def change(
        self,
        business_id: BusinessId,
        apply: Callable[[InboxSettingsDocument], None],
        now: Microseconds,
    ) -> InboxSettingsDocument:
        """
        Change the inbox settings of a business as stored now, in one step
        (default settings are created first when there are none).
        """
        raise NotImplementedError
