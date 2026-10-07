from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.inbox_repositories import (
    ConversationNoteRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.inbox import InboxRefusalCode
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.conversation_notes import (
    DeleteConversationNoteCommand,
    DeletedConversationNote,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.use_cases.inbox.inbox_support import NOTE_ENTITY, append_audit, refusal
from app.use_cases.inbox.notes.note_views import can_delete_note


class DeleteConversationNoteUseCase(
    UseCaseContract[DeleteConversationNoteCommand, DeletedConversationNote]
):
    """
    Delete an internal note: its author may, and an owner may delete any
    (403 `not_note_author` for others). A note of another conversation or
    business is reported missing. Deleting is audited (DELETE of
    "conversation_note") and announced (`conversation.note`).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        note_repo: ConversationNoteRepoContract,
        audit_log_repo: AuditLogRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._note_repo: ConversationNoteRepoContract = note_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: DeleteConversationNoteCommand) -> DeletedConversationNote:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        note: ConversationNoteDocument | None = self._note_repo.get(
            business.id, input_data.note_id
        )
        if note is None or note.conversation_id != input_data.conversation_id:
            raise NotFoundError(f"Note {input_data.note_id} was not found.")

        if not can_delete_note(business, input_data.user_id, note):
            raise AccessDeniedError(
                "Only the author of a note or an owner can delete it.",
                reasons=[
                    refusal(
                        InboxRefusalCode.NOT_NOTE_AUTHOR,
                        "Ask the author or the owner to delete this note.",
                    )
                ],
            )

        self._note_repo.delete(business.id, note.id)
        append_audit(
            self._audit_log_repo,
            business.id,
            input_data.user_id,
            AuditAction.DELETE,
            NOTE_ENTITY,
            str(note.id),
            input_data.client_ip_address,
            self._wall_clock.now_unix(),
        )
        self._live_events.publish(
            business.id,
            LiveEventKind.CONVERSATION_NOTE,
            (note.conversation_id, note.id),
        )
        return DeletedConversationNote(id=note.id, conversation_id=note.conversation_id)
