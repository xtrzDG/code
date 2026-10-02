"""
Persistence contracts of contacts, conversations, messages, LLM turns and calls.

Implementations return independent copies: mutating a returned document does
not change stored state until it is saved. Every business-owned document is
looked up through its business id, so one tenant never sees another's data.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.constrained_integers import (
    ConversationMessageCount,
)
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
from app.schemas.typings.conversations.strings import ChannelUserId, ProviderCallId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber


class ContactRepoContract(RepoContract, Protocol):
    def save(self, contact: ContactDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
    ) -> ContactDocument | None:
        raise NotImplementedError

    def find_by_channel_identity(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
    ) -> ContactDocument | None:
        raise NotImplementedError

    def find_by_phone_number(
        self,
        business_id: BusinessId,
        phone_number: E164PhoneNumber,
    ) -> ContactDocument | None:
        raise NotImplementedError

    def find_by_verified_phone_number(
        self,
        business_id: BusinessId,
        phone_number: E164PhoneNumber,
    ) -> ContactDocument | None:
        """A contact whose phone a channel proved (never a typed phone)."""
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[ContactDocument]:
        raise NotImplementedError

    def delete(self, business_id: BusinessId, contact_id: ContactId) -> None:
        raise NotImplementedError


class ConversationRepoContract(RepoContract, Protocol):
    def save(self, conversation: ConversationDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> ConversationDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ConversationDocument]:
        """Return conversations ordered by last_message_at descending."""
        raise NotImplementedError

    def list_by_contact(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
        last_message_from: Microseconds | None = None,
        status: ConversationStatus | None = None,
    ) -> list[ConversationDocument]:
        """
        One contact's conversations (indexed lookup), ordered by
        last_message_at descending; only those in `status`, and with a
        message at or after `last_message_from`, when given.
        """
        raise NotImplementedError

    def list_by_channel_user(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
    ) -> list[ConversationDocument]:
        """
        One customer's conversations in a channel (indexed lookup), ordered
        by last_message_at descending.
        """
        raise NotImplementedError


class MessageRepoContract(RepoContract, Protocol):
    def save(self, message: MessageDocument) -> None:
        raise NotImplementedError

    def list_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> list[MessageDocument]:
        """Return messages ordered by created_at ascending."""
        raise NotImplementedError

    def count_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        direction: MessageDirection,
        author: MessageAuthor | None = None,
        created_from: Microseconds | None = None,
    ) -> ConversationMessageCount:
        """
        Messages of a conversation in one direction (and by one author, and
        created at or after `created_from`, when given), counted by an
        indexed query.
        """
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[MessageDocument]:
        """Return messages ordered by created_at ascending."""
        raise NotImplementedError

    def delete_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> None:
        """Delete every message of a conversation (visitor data erasure)."""
        raise NotImplementedError


class LlmTurnRepoContract(RepoContract, Protocol):
    def append(self, turn: LlmTurnDocument) -> None:
        """
        Store a new turn; turns are never updated, and are deleted only when
        the visitor's data is erased.
        """
        raise NotImplementedError

    def list_by_conversation(
        self,
        conversation_id: ConversationId,
    ) -> list[LlmTurnDocument]:
        """Return turns ordered by sequence_number ascending."""
        raise NotImplementedError

    def delete_by_conversation(self, conversation_id: ConversationId) -> None:
        """Delete the whole transcript of a conversation (visitor data erasure)."""
        raise NotImplementedError


class CallRepoContract(RepoContract, Protocol):
    def save(self, call: CallDocument) -> None:
        raise NotImplementedError

    def get(self, business_id: BusinessId, call_id: CallId) -> CallDocument | None:
        raise NotImplementedError

    def find_by_provider_call_id(
        self,
        business_id: BusinessId,
        provider_call_id: ProviderCallId,
    ) -> CallDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[CallDocument]:
        raise NotImplementedError
