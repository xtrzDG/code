"""A business, its bookings and the reminder job, ready for one reminder run."""

from datetime import datetime

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.bookings.constrained_integers import BookingReminderLeadSeconds
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.platform.constrained_strings import JobName
from app.transformers.notifications.booking_reminder_template_transformer import (
    BookingReminderTemplateTransformer,
)
from app.transformers.notifications.booking_reminder_transformer import (
    BookingReminderTransformer,
)
from app.use_cases.bookings.reminders.send_booking_reminders_use_case import (
    SendBookingRemindersUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.operations.builders import DEFAULT_NOW
from tests.operations.fakes import to_microseconds
from tests.operations.operations_world import OperationsWorld
from tests.operations.reminder_channel_sender import RecordingChannelSender

# DEFAULT_NOW is Monday 2026-10-05 08:00 UTC = 12:00 in Tbilisi (UTC+4).
TICK: JobTick = JobTick(
    job_name=JobName("send_booking_reminders"),
    scheduled_at=to_microseconds(DEFAULT_NOW),
)


class ReminderScene:
    """A Georgian restaurant with one table, its customer and the job."""

    def __init__(
        self,
        failing_channels: frozenset[ChannelKind] = frozenset(),
        reminder_lead: BookingReminderLeadSeconds | None = None,
        reminder_template: str | None = "booking_reminder",
    ) -> None:
        self.world = OperationsWorld()
        self.business: BusinessDocument = self.world.add_business()
        self.world.add_profile(self.business)
        self.table: ResourceDocument = self.world.add_resource(self.business, "Table 1")
        self.sender = RecordingChannelSender(failing_channels)
        self.reminders = SendBookingRemindersUseCase(
            business_repo=self.world.business_repo,
            business_profile_repo=self.world.profile_repo,
            booking_repo=self.world.booking_repo,
            resource_repo=self.world.resource_repo,
            contact_repo=self.world.contact_repo,
            conversation_repo=self.world.conversation_repo,
            message_repo=self.world.message_repo,
            channel_message_sender=self.sender,
            reminder_transformer=BookingReminderTransformer(LocalizedTextResolver()),
            reminder_template_transformer=BookingReminderTemplateTransformer(),
            wall_clock=self.world.clock.wall_clock,
            whatsapp_reminder_template=(
                None
                if reminder_template is None
                else WhatsAppTemplateName(reminder_template)
            ),
            **({} if reminder_lead is None else {"reminder_lead": reminder_lead}),
        )

    def customer_wrote(
        self,
        contact: ContactDocument,
        channel: ChannelKind,
        hours_ago: float,
        business: BusinessDocument | None = None,
    ) -> None:
        """The customer's last message in a channel, some hours before now."""

        moment = Microseconds(
            int(to_microseconds(DEFAULT_NOW)) - int(hours_ago * 3_600_000_000)
        )
        owner = business or self.business
        conversation = ConversationDocument(
            business_id=owner.id,
            contact_id=contact.id,
            assistant_version_id=AssistantVersionId(),
            channel=channel,
            channel_user_id=contact.channel_identities[0].channel_user_id,
            last_message_at=moment,
            created_at=moment,
            updated_at=moment,
        )
        self.world.conversation_repo.save(conversation)
        self.world.message_repo.save(
            MessageDocument(
                conversation_id=conversation.id,
                business_id=owner.id,
                direction=MessageDirection.INBOUND,
                author=MessageAuthor.CUSTOMER,
                text=MessageText("Hi"),
                created_at=moment,
                updated_at=moment,
            )
        )

    def add_customer(
        self,
        identities: dict[ChannelKind, str],
        language: str | None = "ka",
        business: BusinessDocument | None = None,
    ) -> ContactDocument:
        contact = self.world.add_contact(
            business or self.business,
            name="Nino",
            phone="+995555123456",
            language=language,
        )
        contact.channel_identities = [
            ChannelIdentity(channel=channel, channel_user_id=ChannelUserId(user_id))
            for channel, user_id in identities.items()
        ]
        self.world.contact_repo.save(contact)
        return contact

    def add_booking(
        self,
        contact: ContactDocument,
        starts: str,
        source_channel: ChannelKind = ChannelKind.WHATSAPP,
        status: BookingStatus = BookingStatus.CONFIRMED,
        is_sandbox: bool = False,
        business: BusinessDocument | None = None,
        resource: ResourceDocument | None = None,
    ) -> BookingDocument:
        starts_at = datetime.fromisoformat(starts)
        ends_at = starts_at.replace(hour=(starts_at.hour + 2) % 24)
        booking = self.world.add_booking(
            business or self.business,
            resource or self.table,
            contact,
            starts=starts_at.isoformat(),
            ends=ends_at.isoformat(),
            status=status,
            is_sandbox=is_sandbox,
        )
        booking.source_channel = source_channel
        self.world.booking_repo.save(booking)
        return booking

    def run(self) -> JobReport:
        return self.reminders.run(TICK)

    def stored(self, booking: BookingDocument) -> BookingDocument:
        stored = self.world.booking_repo.get(booking.business_id, booking.id)
        assert stored is not None
        return stored

    def usage_events(self) -> int:
        """Usage the job itself recorded (the channel sender meters sends)."""

        return len(
            self.world.usage_repo.list_by_business_between(
                self.business.id,
                to_microseconds(datetime.fromisoformat("2026-01-01T00:00:00+00:00")),
                to_microseconds(datetime.fromisoformat("2027-01-01T00:00:00+00:00")),
            )
        )
