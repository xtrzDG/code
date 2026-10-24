from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.inbox_repositories import (
    ConversationNoteRepoContract,
    ConversationTeamRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.conversation_notes import (
    ConversationNoteView,
    CreateConversationNoteCommand,
)
from app.use_cases.inbox.inbox_support import (
    NOTE_ENTITY,
    append_audit,
    require_conversation,
)
from app.use_cases.inbox.notes.note_views import author_names, build_note_view


class CreateConversationNoteUseCase(
    UseCaseContract[CreateConversationNoteCommand, ConversationNoteView]
):
    """
    A member leaves an internal note on a conversation ("called back,
    prefers Saturday"). Notes live in their own collection, apart from the
    messages, so the conversation turn, the replies to the customer and
    the customer's widget never read them. Writing one is audited (CREATE
    of "conversation_note") and announced (`conversation.note`, ids only)
    so the team's open cards show it.
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
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationTeamRepoContract = conversation_repo
        self._note_repo: ConversationNoteRepoContract = note_repo
        self._user_repo: UserRepoContract = user_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CreateConversationNoteCommand) -> ConversationNoteView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        conversation: ConversationDocument = require_conversation(
            self._conversation_repo, business.id, input_data.conversation_id
        )
        now: Microseconds = self._wall_clock.now_unix()
        note = ConversationNoteDocument(
            business_id=business.id,
            conversation_id=conversation.id,
            author_user_id=input_data.user_id,
            text=input_data.text,
            created_at=now,
            updated_at=now,
        )
        self._note_repo.add(note)
        append_audit(
            self._audit_log_repo,
            business.id,
            input_data.user_id,
            AuditAction.CREATE,
            NOTE_ENTITY,
            str(note.id),
            input_data.client_ip_address,
            now,
        )
        self._live_events.publish(
            business.id,
            LiveEventKind.CONVERSATION_NOTE,
            (conversation.id, note.id),
            is_sandbox=conversation.is_sandbox,
        )
        return build_note_view(
            note, author_names(self._user_repo, [note]), can_delete=True
        )
