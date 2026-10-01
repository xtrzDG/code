import logging
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ChannelMessageSenderFacilitatorContract
from app.contracts.repositories import (
    BookingRepoContract,
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ContactRepoContract,
    ResourceRepoContract,
    UsageEventRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.operations import BookingMessageInput
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.billing.constrained_integers import UsageQuantity
from app.schemas.typings.bookings.constrained_integers import (
    BookingReminderLeadSeconds,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.profiles.strings import CancellationPolicyText
from app.use_cases.bookings.booking_support import booking_unit_of
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
)

logger: logging.Logger = logging.getLogger(__name__)

# The concept's reminder goes out the day before (configurable per process).
DEFAULT_REMINDER_LEAD: BookingReminderLeadSeconds = BookingReminderLeadSeconds(
    24 * 60 * 60
)
# Channels a reminder can be written to, best first after the booking's own
# channel: Telegram has no messaging window and costs nothing; WhatsApp is
# where most customers are.
MESSAGING_CHANNELS: tuple[ChannelKind, ...] = (
    ChannelKind.TELEGRAM,
    ChannelKind.WHATSAPP,
    ChannelKind.MESSENGER,
    ChannelKind.INSTAGRAM,
)
# WhatsApp reminders are template messages (concept section 6), metered as
# such: one per reminder.
WHATSAPP_REMINDER_QUANTITY: UsageQuantity = UsageQuantity(1)


class SendBookingRemindersUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job: remind customers of their upcoming bookings (concept:
    "с подтверждением и напоминанием").

    Every CONFIRMED, non-sandbox booking that starts within the reminder lead
    (24 hours by default) and has not been reminded gets one localized
    message: business name, date and time in the business time zone, and how
    to cancel or move it. It goes to the customer's identity in the
    booking's own channel; bookings made by phone or on the website (or when
    that identity is missing) use another messenger the customer is known
    in. Customers known only by phone or web chat are skipped.

    A delivery failure is logged and the booking stays unreminded, so the
    next run tries again until the booking starts. Businesses the owner
    paused, and businesses whose unpaid subscription switched the assistant
    to leads only, send no reminders.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        booking_repo: BookingRepoContract,
        resource_repo: ResourceRepoContract,
        contact_repo: ContactRepoContract,
        usage_event_repo: UsageEventRepoContract,
        channel_message_sender: ChannelMessageSenderFacilitatorContract,
        reminder_transformer: TransformerContract[BookingMessageInput, MessageText],
        wall_clock: WallClock[Microseconds],
        reminder_lead: BookingReminderLeadSeconds = DEFAULT_REMINDER_LEAD,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._channel_message_sender: ChannelMessageSenderFacilitatorContract = (
            channel_message_sender
        )
        self._reminder_transformer: TransformerContract[
            BookingMessageInput, MessageText
        ] = reminder_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._reminder_lead: BookingReminderLeadSeconds = reminder_lead

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        now_seconds: int = microseconds_to_seconds(int(now))
        window_end_seconds: int = now_seconds + int(self._reminder_lead)
        reminded: int = 0
        for business in self._business_repo.list_all():
            if not sends_reminders(business):
                continue

            due_bookings: list[BookingDocument] = [
                booking
                for booking in self._booking_repo.list_by_business(business.id)
                if is_reminder_due(booking, now_seconds, window_end_seconds)
            ]
            if not due_bookings:
                continue

            zone: ZoneInfo = load_time_zone(business.timezone)
            cancellation_policy: CancellationPolicyText | None = (
                self._read_cancellation_policy(business)
            )
            for booking in due_bookings:
                if self._remind(business, zone, cancellation_policy, booking, now):
                    reminded += 1

        return JobReport(processed_count=ProcessedItemCount(reminded))

    def _remind(
        self,
        business: BusinessDocument,
        zone: ZoneInfo,
        cancellation_policy: CancellationPolicyText | None,
        booking: BookingDocument,
        now: Microseconds,
    ) -> bool:
        contact: ContactDocument | None = self._contact_repo.get(
            business.id,
            booking.contact_id,
        )
        if contact is None:
            return False

        identities: list[ChannelIdentity] = choose_reminder_identities(
            contact,
            booking.source_channel,
        )
        if not identities:
            return False

        resource: ResourceDocument | None = self._resource_repo.get(
            business.id,
            booking.resource_id,
        )
        text: MessageText = self._reminder_transformer.transform(
            BookingMessageInput(
                business_name=business.name,
                booking=build_booking_view(
                    booking,
                    business.timezone,
                    zone,
                    resource,
                    contact,
                ),
                booking_unit=booking_unit_of(resource),
                language=choose_reminder_language(contact, business),
                cancellation_policy=cancellation_policy,
            )
        )
        for identity in identities:
            try:
                self._channel_message_sender.send(
                    business.id,
                    identity.channel,
                    identity.channel_user_id,
                    text,
                )
            except ApplicationError as error:
                logger.warning(
                    "Reminder of booking %s through %s failed: %s",
                    booking.id,
                    identity.channel.value,
                    error,
                )
                continue

            self._record_delivery(business, booking, identity.channel, now)
            return True

        return False

    def _record_delivery(
        self,
        business: BusinessDocument,
        booking: BookingDocument,
        channel: ChannelKind,
        now: Microseconds,
    ) -> None:
        if channel is ChannelKind.WHATSAPP:
            self._usage_event_repo.append(
                UsageEventDocument(
                    business_id=business.id,
                    conversation_id=booking.conversation_id,
                    kind=UsageKind.WHATSAPP_TEMPLATE,
                    quantity=WHATSAPP_REMINDER_QUANTITY,
                    occurred_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )

        booking.reminder_sent_at = now
        booking.updated_at = now
        self._booking_repo.save(booking)

    def _read_cancellation_policy(
        self,
        business: BusinessDocument,
    ) -> CancellationPolicyText | None:
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        if profile is None or profile.booking_rules is None:
            return None

        return profile.booking_rules.cancellation_policy


def sends_reminders(business: BusinessDocument) -> bool:
    """Paused businesses and leads-only service send no reminders."""

    return (
        business.status is not BusinessStatus.PAUSED
        and business.service_mode is ServiceMode.FULL
    )


def is_reminder_due(
    booking: BookingDocument,
    now_seconds: int,
    window_end_seconds: int,
) -> bool:
    """Confirmed, real, not yet reminded, starting within the window."""

    return (
        booking.status is BookingStatus.CONFIRMED
        and not booking.is_sandbox
        and booking.reminder_sent_at is None
        and now_seconds < int(booking.starts_at) <= window_end_seconds
    )


def choose_reminder_identities(
    contact: ContactDocument,
    source_channel: ChannelKind,
) -> list[ChannelIdentity]:
    """
    Messaging identities to try, best first: the booking's own channel, then
    the other messengers the customer is known in. Phone and web chat cannot
    carry a message later, so they are never used.
    """

    preferred_channels: list[ChannelKind] = [
        channel
        for channel in (source_channel, *MESSAGING_CHANNELS)
        if channel in MESSAGING_CHANNELS
    ]
    identities: list[ChannelIdentity] = []
    for channel in preferred_channels:
        for identity in contact.channel_identities:
            if identity.channel is channel and identity not in identities:
                identities.append(identity)

    return identities


def choose_reminder_language(
    contact: ContactDocument,
    business: BusinessDocument,
) -> LanguageTag:
    """The customer's language when known, else the business default."""

    if contact.language is not None:
        return contact.language

    return business.default_language
