"""Notes as the cabinet reads them: with the author's name."""

from collections.abc import Sequence

from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.inbox.conversation_notes import ConversationNoteView
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName
from app.use_cases.inbox.inbox_support import is_owner


def author_names(
    user_repo: UserRepoContract,
    notes: Sequence[ConversationNoteDocument],
) -> dict[UserId, UserDisplayName]:
    """The display names of the authors of the notes (each read once)."""

    names: dict[UserId, UserDisplayName] = {}
    for author_id in dict.fromkeys(note.author_user_id for note in notes):
        user: UserDocument | None = user_repo.get(author_id)
        if user is not None and user.display_name is not None:
            names[author_id] = user.display_name

    return names


def can_delete_note(
    business: BusinessDocument,
    viewer: UserId,
    note: ConversationNoteDocument,
) -> bool:
    """The author deletes their own note; an owner deletes any."""

    return note.author_user_id == viewer or is_owner(business, viewer)


def build_note_view(
    note: ConversationNoteDocument,
    names: dict[UserId, UserDisplayName],
    can_delete: bool,
) -> ConversationNoteView:
    return ConversationNoteView(
        id=note.id,
        conversation_id=note.conversation_id,
        author_user_id=note.author_user_id,
        author_name=names.get(note.author_user_id),
        text=note.text,
        created_at=note.created_at,
        can_delete=can_delete,
    )
