from typed_time_provider import Microseconds

from app.registries.demo.demo_clock import MICROSECONDS_PER_SECOND, DemoClock
from app.schemas.constants.bookings import BookingStatus, LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import HandoffReason, HandoffStatus, HandoffUrgency
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.bookings.strings import (
    BookingNote,
    LeadBudgetText,
    LeadDetails,
)
from app.schemas.typings.handoffs.constrained_integers import QuestionOccurrenceCount
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.handoffs.strings import HandoffSummary, UnansweredQuestionText
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import LanguageTag

# The concept's reminder lead: bookings this close get their reminder.
REMINDER_LEAD_SECONDS: int = 24 * 60 * 60
# Channels the reminder job writes to (send_booking_reminders_use_case).
REMINDER_CHANNELS: frozenset[ChannelKind] = frozenset(
    {
        ChannelKind.TELEGRAM,
        ChannelKind.WHATSAPP,
        ChannelKind.MESSENGER,
        ChannelKind.INSTAGRAM,
    }
)


class DemoOperationsRecorder:
    """
    What customers asked for in a demo business: bookings of its resources,
    leads for managers, handoffs to staff and questions the knowledge did
    not answer.

    Upcoming confirmed bookings of customers known in a messenger are only
    allowed within the reminder lead (their reminder counts as sent), so
    the reminder job never writes through the made-up channel credentials.
    """

    def __init__(
        self,
        business: BusinessDocument,
        clock: DemoClock,
        resources: list[ResourceDocument],
    ) -> None:
        self._business: BusinessDocument = business
        self._clock: DemoClock = clock
        self._resources: list[ResourceDocument] = resources
        self.bookings: list[BookingDocument] = []
        self.leads: list[LeadDocument] = []
        self.handoffs: list[HandoffDocument] = []
        self.questions: list[UnansweredQuestionDocument] = []

    def resource(self, name: str) -> ResourceDocument:
        for resource in self._resources:
            if str(resource.name) == name:
                return resource

        raise ValueError(f"The demo business has no resource {name!r}.")

    def booking(
        self,
        contact: ContactDocument,
        resource_name: str,
        start: Microseconds,
        party_size: int,
        channel: ChannelKind,
        status: BookingStatus = BookingStatus.CONFIRMED,
        minutes: int = 120,
        conversation: ConversationDocument | None = None,
        notes: str | None = None,
        made_at: Microseconds | None = None,
        booking_id: BookingId | None = None,
    ) -> BookingDocument:
        created: Microseconds = made_at or (
            conversation.last_message_at
            if conversation is not None
            else self._clock.later(start, -3 * 24 * 60)
        )
        booking = BookingDocument(
            id=booking_id or BookingId(),
            business_id=self._business.id,
            resource_id=self.resource(resource_name).id,
            contact_id=contact.id,
            conversation_id=None if conversation is None else conversation.id,
            starts_at=self._clock.booking_start(start),
            ends_at=self._clock.booking_end(start, minutes),
            party_size=PartySize(party_size),
            status=status,
            source_channel=channel,
            notes=None if notes is None else BookingNote(notes),
            language=contact.language,
            reminder_sent_at=self._reminder_moment(contact, start, created, status),
            created_at=created,
            updated_at=created,
        )
        self.bookings.append(booking)
        return booking

    def lead(
        self,
        contact: ContactDocument,
        lead_type: LeadType,
        details: str,
        channel: ChannelKind,
        made_at: Microseconds,
        status: LeadStatus = LeadStatus.NEW,
        conversation: ConversationDocument | None = None,
        requested_day: int | None = None,
        party_size: int | None = None,
        budget: str | None = None,
        lead_id: LeadId | None = None,
    ) -> LeadDocument:
        lead = LeadDocument(
            id=lead_id or LeadId(),
            business_id=self._business.id,
            contact_id=contact.id,
            conversation_id=None if conversation is None else conversation.id,
            lead_type=lead_type,
            details=LeadDetails(details),
            requested_date=(
                None if requested_day is None else self._clock.date(requested_day)
            ),
            party_size=None if party_size is None else PartySize(party_size),
            budget=None if budget is None else LeadBudgetText(budget),
            source_channel=channel,
            status=status,
            created_at=made_at,
            updated_at=made_at,
        )
        self.leads.append(lead)
        return lead

    def handoff(
        self,
        conversation: ConversationDocument,
        reason: HandoffReason,
        summary: str,
        urgency: HandoffUrgency = HandoffUrgency.NORMAL,
        resolved_after_minutes: int | None = None,
        handoff_id: HandoffId | None = None,
    ) -> HandoffDocument:
        """Handed off at the conversation's last message; open unless resolved."""

        made_at: Microseconds = conversation.last_message_at
        is_resolved: bool = resolved_after_minutes is not None
        handoff = HandoffDocument(
            id=handoff_id or HandoffId(),
            business_id=self._business.id,
            conversation_id=conversation.id,
            contact_id=conversation.contact_id,
            reason=reason,
            summary=HandoffSummary(summary),
            urgency=urgency,
            status=HandoffStatus.RESOLVED if is_resolved else HandoffStatus.NOTIFIED,
            resolved_at=(
                self._clock.later(made_at, resolved_after_minutes)
                if resolved_after_minutes is not None
                else None
            ),
            created_at=made_at,
            updated_at=made_at,
        )
        if not is_resolved:
            conversation.status = ConversationStatus.HANDOFF

        self.handoffs.append(handoff)
        return handoff

    def question(
        self,
        text: str,
        language: str,
        last_seen: Microseconds,
        occurrences: int = 1,
        answered_by: KnowledgeItemId | None = None,
        question_id: UnansweredQuestionId | None = None,
    ) -> UnansweredQuestionDocument:
        question = UnansweredQuestionDocument(
            id=question_id or UnansweredQuestionId(),
            business_id=self._business.id,
            question=UnansweredQuestionText(text),
            language=LanguageTag(language),
            occurrence_count=QuestionOccurrenceCount(occurrences),
            last_seen_at=last_seen,
            is_resolved=answered_by is not None,
            resolved_knowledge_item_id=answered_by,
            created_at=self._clock.later(last_seen, -occurrences * 26 * 60),
            updated_at=last_seen,
        )
        self.questions.append(question)
        return question

    def _reminder_moment(
        self,
        contact: ContactDocument,
        start: Microseconds,
        created: Microseconds,
        status: BookingStatus,
    ) -> Microseconds | None:
        reminder: int = int(start) - REMINDER_LEAD_SECONDS * MICROSECONDS_PER_SECOND
        has_messenger: bool = any(
            identity.channel in REMINDER_CHANNELS
            for identity in contact.channel_identities
        )
        if not has_messenger or status is BookingStatus.CANCELLED:
            return None

        if reminder > int(self._clock.now):
            if status is BookingStatus.CONFIRMED:
                raise ValueError(
                    f"Demo booking of {contact.name} is further away than the "
                    "reminder lead: the reminder job would write to the demo "
                    "channel credentials."
                )
            return None

        return Microseconds(max(reminder, int(created)))
