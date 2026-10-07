from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.inbox_repositories import (
    ConversationNoteRepoContract,
    ConversationTeamRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.conversation_notes import (
    ConversationNotePage,
    ConversationNotesQuery,
)
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.inbox.inbox_support import (
    NOTE_ENTITY,
    append_audit,
    require_conversation,
)
from app.use_cases.inbox.notes.note_views import (
    author_names,
    build_note_view,
    can_delete_note,
)
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListConversationNotesUseCase(
    UseCaseContract[ConversationNotesQuery, ConversationNotePage]
):
    """
    One page of a conversation's internal notes, newest first (a keyset
    page in the database), for owners and staff, each with its author's
    name and whether the viewer may delete it. Reading notes is audited
    (VIEW of "conversation_note", the conversation as the reference).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationTeamRepoContract,
        note_repo: ConversationNoteRepoContract,
        user_repo: UserRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationTeamRepoContract = conversation_repo
        self._note_repo: ConversationNoteRepoContract = note_repo
        self._user_repo: UserRepoContract = user_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ConversationNotesQuery) -> ConversationNotePage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        conversation: ConversationDocument = require_conversation(
            self._conversation_repo, business.id, input_data.conversation_id
        )
        notes: list[ConversationNoteDocument]
        next_cursor: PageCursor | None
        notes, next_cursor = finish_page(
            self._note_repo.page_by_conversation(
                business.id, conversation.id, read_slice(input_data.page)
            ),
            input_data.page,
            sort_key=lambda note: int(note.created_at),
            item_id=lambda note: str(note.id),
        )
        append_audit(
            self._audit_log_repo,
            business.id,
            input_data.user_id,
            AuditAction.VIEW,
            NOTE_ENTITY,
            str(conversation.id),
            input_data.client_ip_address,
            self._wall_clock.now_unix(),
        )
        names = author_names(self._user_repo, notes)
        return ConversationNotePage(
            items=[
                build_note_view(
                    note, names, can_delete_note(business, input_data.user_id, note)
                )
                for note in notes
            ],
            next_cursor=next_cursor,
        )
