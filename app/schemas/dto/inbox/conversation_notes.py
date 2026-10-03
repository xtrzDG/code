"""Internal notes of the team on a conversation."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.dto.paging import PageRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.inbox.booleans import CanDeleteConversationNote
from app.schemas.typings.inbox.constrained_strings import ConversationNoteText
from app.schemas.typings.inbox.prefixed_id import ConversationNoteId
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName


class ConversationNoteRequest(ImmutableDTO):
    """Body of POST .../conversations/{conversation_id}/notes."""

    text: ConversationNoteText


class CreateConversationNoteCommand(ImmutableDTO):
    """A member leaves a note on a conversation (audited)."""

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    text: ConversationNoteText
    client_ip_address: ClientIpAddress | None = None


class ConversationNotesQuery(ImmutableDTO):
    """One page of the notes of a conversation, newest first (audited)."""

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    page: PageRequest = Field(default_factory=PageRequest)
    client_ip_address: ClientIpAddress | None = None


class DeleteConversationNoteCommand(ImmutableDTO):
    """The author or an owner deletes a note (audited)."""

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    note_id: ConversationNoteId
    client_ip_address: ClientIpAddress | None = None


class ConversationNoteView(ImmutableDTO):
    """
    A note with its author's name; `can_delete` tells the viewer whether
    they may delete it (their own note, or any note for an owner).
    """

    id: ConversationNoteId
    conversation_id: ConversationId
    author_user_id: UserId
    author_name: UserDisplayName | None = None
    text: ConversationNoteText
    created_at: Microseconds
    can_delete: CanDeleteConversationNote = False


class ConversationNotePage(ImmutableDTO):
    """One page of notes, newest first; `next_cursor` asks for older ones."""

    items: list[ConversationNoteView] = Field(
        default_factory=list[ConversationNoteView]
    )
    next_cursor: PageCursor | None = None
