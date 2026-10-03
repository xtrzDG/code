"""
In-memory stand-ins for the tools that act for a contact: lead, handoff to
a human and the unanswered-question record.

Each fake remembers the commands it received, so tests can check that
business, contact, conversation and channel came from the server.
"""

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import HandoffRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import LeadStatus
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.bookings import CreateLeadCommand, LeadView
from app.schemas.dto.handoffs import (
    CodedHandoffSummary,
    HandoffCommand,
    HandoffResult,
    RecordUnansweredQuestionCommand,
    UnansweredQuestionView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.prefixed_id import LeadId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import UnansweredQuestionId
from app.schemas.typings.handoffs.strings import HandoffSummary


class FakeCreateLead(UseCaseContract[CreateLeadCommand, LeadView]):
    def __init__(self) -> None:
        self.commands: list[CreateLeadCommand] = []

    def run(self, input_data: CreateLeadCommand) -> LeadView:
        self.commands.append(input_data)
        return LeadView(
            id=LeadId(),
            business_id=input_data.business_id,
            contact_id=input_data.contact_id,
            lead_type=input_data.lead_type,
            details=input_data.details,
            requested_date=input_data.requested_date,
            party_size=input_data.party_size,
            budget=input_data.budget,
            source_channel=input_data.source_channel,
            status=LeadStatus.NEW,
            is_sandbox=input_data.is_sandbox,
        )


class FakeHandoff(UseCaseContract[HandoffCommand, HandoffResult]):
    """Stores the handoff and switches the conversation to HANDOFF, like staff tools."""

    def __init__(
        self,
        handoff_repo: HandoffRepoContract,
        conversation_repo: ConversationRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self.commands: list[HandoffCommand] = []
        self.is_failing: bool = False

    def run(self, input_data: HandoffCommand) -> HandoffResult:
        self.commands.append(input_data)
        if self.is_failing:
            raise NotFoundError("Conversation was not found.")

        now: Microseconds = self._wall_clock.now_unix()
        coded: CodedHandoffSummary | None = None
        summary: HandoffSummary
        if isinstance(input_data.summary, CodedHandoffSummary):
            coded = input_data.summary
            # The real use case renders it in the staff language.
            summary = HandoffSummary(f"[{coded.code.value}]")
        else:
            summary = input_data.summary

        handoff = HandoffDocument(
            business_id=input_data.business_id,
            conversation_id=input_data.conversation_id,
            contact_id=input_data.contact_id,
            reason=input_data.reason,
            summary=summary,
            summary_code=None if coded is None else coded.code,
            quoted_text=None if coded is None else coded.quoted_text,
            flagged_values=[] if coded is None else list(coded.flagged_values),
            urgency=input_data.urgency,
            is_sandbox=input_data.is_sandbox,
            created_at=now,
            updated_at=now,
        )
        self._handoff_repo.save(handoff)
        conversation: ConversationDocument | None = self._conversation_repo.get(
            input_data.business_id, input_data.conversation_id
        )
        if conversation is not None:
            conversation.status = ConversationStatus.HANDOFF
            self._conversation_repo.save(conversation)

        return HandoffResult(
            id=handoff.id,
            business_id=input_data.business_id,
            conversation_id=input_data.conversation_id,
            reason=input_data.reason,
            urgency=input_data.urgency,
            status=HandoffStatus.NOTIFIED,
            customer_message=MessageText(
                f"[{input_data.language}] A colleague will reply soon."
            ),
        )


class FakeRecordUnansweredQuestion(
    UseCaseContract[RecordUnansweredQuestionCommand, UnansweredQuestionView]
):
    def __init__(self) -> None:
        self.commands: list[RecordUnansweredQuestionCommand] = []

    def run(
        self, input_data: RecordUnansweredQuestionCommand
    ) -> UnansweredQuestionView:
        self.commands.append(input_data)
        return UnansweredQuestionView(
            id=UnansweredQuestionId(),
            business_id=input_data.business_id,
            question=input_data.question,
            language=input_data.language,
        )


def contact_ids_of(commands: list[object]) -> set[ContactId]:
    """Contact ids carried by recorded commands (for isolation checks)."""

    return {
        contact_id
        for command in commands
        if isinstance(contact_id := getattr(command, "contact_id", None), ContactId)
    }
