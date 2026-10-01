"""
In-memory stand-ins for the tool use cases other slices build.

Each fake implements the same UseCaseContract the conversation engine
depends on and remembers the commands it received, so tests can check
that business, contact, conversation and channel came from the server.
"""

from dataclasses import dataclass, field

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import ConversationRepoContract, HandoffRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import (
    BookingStatus,
    BookingUnit,
    LeadStatus,
)
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    AvailableSlot,
    BookingResult,
    BookingView,
    CancelBookingCommand,
    CreateBookingCommand,
    CreateLeadCommand,
    LeadView,
    RescheduleBookingCommand,
)
from app.schemas.dto.handoffs import (
    HandoffCommand,
    HandoffResult,
    RecordUnansweredQuestionCommand,
    UnansweredQuestionView,
)
from app.schemas.dto.knowledge import (
    KnowledgeItemView,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    PriceLookupQuery,
    PriceLookupResult,
    SendLinkQuery,
    SendLinkResult,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId, ResourceId
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import UnansweredQuestionId
from app.schemas.typings.localization.constrained_strings import TimezoneName

TABLE_RESOURCE_ID: ResourceId = ResourceId()


class FakeSearchKnowledge(
    UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult]
):
    def __init__(self, items: list[KnowledgeItemView]) -> None:
        self.items: list[KnowledgeItemView] = items
        self.requests: list[KnowledgeSearchRequest] = []

    def run(self, input_data: KnowledgeSearchRequest) -> KnowledgeSearchResult:
        self.requests.append(input_data)
        query: str = str(input_data.query).casefold()
        matches: list[KnowledgeItemView] = [
            item
            for item in self.items
            if query in str(item.title).casefold()
            or (item.body is not None and query in str(item.body).casefold())
        ]
        return KnowledgeSearchResult(items=matches[: int(input_data.limit)])


class FakeGetPrice(UseCaseContract[PriceLookupQuery, PriceLookupResult]):
    def __init__(self, items: list[KnowledgeItemView]) -> None:
        self.items: list[KnowledgeItemView] = items
        self.queries: list[PriceLookupQuery] = []

    def run(self, input_data: PriceLookupQuery) -> PriceLookupResult:
        self.queries.append(input_data)
        name: str = str(input_data.item_name).casefold()
        return PriceLookupResult(
            matches=[
                item
                for item in self.items
                if item.price_minor is not None and name in str(item.title).casefold()
            ]
        )


class FakeSendLink(UseCaseContract[SendLinkQuery, SendLinkResult]):
    def __init__(self, links: dict[BusinessLinkKind, WebLink]) -> None:
        self.links: dict[BusinessLinkKind, WebLink] = links

    def run(self, input_data: SendLinkQuery) -> SendLinkResult:
        return SendLinkResult(kind=input_data.kind, url=self.links.get(input_data.kind))


class FakeCheckAvailability(UseCaseContract[AvailabilityQuery, AvailabilityResult]):
    def __init__(self, timezone: TimezoneName, free_times: list[str]) -> None:
        self.timezone: TimezoneName = timezone
        self.free_times: list[str] = free_times
        self.queries: list[AvailabilityQuery] = []

    def run(self, input_data: AvailabilityQuery) -> AvailabilityResult:
        self.queries.append(input_data)
        return AvailabilityResult(
            timezone=self.timezone,
            is_open_on_date=True,
            slots=[
                AvailableSlot(
                    resource_id=TABLE_RESOURCE_ID,
                    resource_name=ResourceName("Table by the window"),
                    booking_unit=BookingUnit.TIME_SLOT,
                    date=input_data.date,
                    time=LocalTimeOfDay(free_time),
                )
                for free_time in self.free_times
            ],
        )


@dataclass
class FakeBookings:
    """create, cancel and reschedule over one in-memory list."""

    timezone: TimezoneName
    is_slot_taken: bool = False
    commands: list[object] = field(default_factory=list[object])
    bookings: dict[BookingId, BookingView] = field(
        default_factory=dict[BookingId, BookingView]
    )

    def create(self, command: CreateBookingCommand) -> BookingResult:
        self.commands.append(command)
        if self.is_slot_taken:
            raise ConflictError("This time is already taken; offer another slot.")

        booking = BookingView(
            id=BookingId(),
            business_id=command.business_id,
            resource_id=TABLE_RESOURCE_ID,
            resource_name=ResourceName("Table by the window"),
            contact_id=command.contact_id,
            contact_name=command.contact_name,
            contact_phone_number=command.contact_phone_number,
            date=command.date,
            time=command.time,
            end_date=command.date,
            end_time=None,
            timezone=self.timezone,
            party_size=command.party_size,
            status=BookingStatus.CONFIRMED,
            source_channel=command.source_channel,
            notes=command.notes,
            is_sandbox=command.is_sandbox,
            conversation_id=command.conversation_id,
            language=command.language,
            created_at=Microseconds(1_790_000_000_000_000),
        )
        self.bookings[booking.id] = booking
        return BookingResult(
            booking=booking,
            confirmation_text=MessageText(f"Booked for {command.date} {command.time}."),
        )

    def cancel(self, command: CancelBookingCommand) -> BookingResult:
        self.commands.append(command)
        booking: BookingView | None = (
            None
            if command.booking_id is None
            else self.bookings.get(command.booking_id)
        )
        if booking is None:
            raise NotFoundError("No booking was found for these details.")

        cancelled: BookingView = booking.model_copy(
            update={"status": BookingStatus.CANCELLED}
        )
        self.bookings[booking.id] = cancelled
        return BookingResult(
            booking=cancelled,
            confirmation_text=MessageText("The booking is cancelled."),
        )

    def reschedule(self, command: RescheduleBookingCommand) -> BookingResult:
        self.commands.append(command)
        booking: BookingView | None = (
            None
            if command.booking_id is None
            else self.bookings.get(command.booking_id)
        )
        if booking is None:
            raise NotFoundError("No booking was found for these details.")

        moved: BookingView = booking.model_copy(
            update={
                "date": command.new_date,
                "end_date": command.new_date,
                "time": command.new_time,
            }
        )
        self.bookings[booking.id] = moved
        return BookingResult(
            booking=moved,
            confirmation_text=MessageText(f"Moved to {command.new_date}."),
        )


class FakeCreateBooking(UseCaseContract[CreateBookingCommand, BookingResult]):
    def __init__(self, bookings: FakeBookings) -> None:
        self._bookings: FakeBookings = bookings

    def run(self, input_data: CreateBookingCommand) -> BookingResult:
        return self._bookings.create(input_data)


class FakeCancelBooking(UseCaseContract[CancelBookingCommand, BookingResult]):
    def __init__(self, bookings: FakeBookings) -> None:
        self._bookings: FakeBookings = bookings

    def run(self, input_data: CancelBookingCommand) -> BookingResult:
        return self._bookings.cancel(input_data)


class FakeRescheduleBooking(UseCaseContract[RescheduleBookingCommand, BookingResult]):
    def __init__(self, bookings: FakeBookings) -> None:
        self._bookings: FakeBookings = bookings

    def run(self, input_data: RescheduleBookingCommand) -> BookingResult:
        return self._bookings.reschedule(input_data)


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
        handoff = HandoffDocument(
            business_id=input_data.business_id,
            conversation_id=input_data.conversation_id,
            contact_id=input_data.contact_id,
            reason=input_data.reason,
            summary=input_data.summary,
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
