import logging
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ChannelMessageSenderFacilitatorContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.operations import BookingMessageInput
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.bookings.constrained_integers import (
    BookingReminderLeadSeconds,
)
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
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
MICROSECONDS_PER_SECOND: int = 1_000_000

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
# Free-form messages are allowed within 24 hours of the customer's last
# message in WhatsApp, Messenger and Instagram (concept section 6); later
# a WhatsApp reminder is an approved template, and the other two skip.
CUSTOMER_SERVICE_WINDOW_SECONDS: int = 24 * 60 * 60
WINDOWED_CHANNELS: frozenset[ChannelKind] = frozenset(
    {ChannelKind.WHATSAPP, ChannelKind.MESSENGER, ChannelKind.INSTAGRAM}
)


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

    WhatsApp, Messenger and Instagram accept free-form text only within 24
    hours of the customer's last message there (concept section 6). Later,
    a WhatsApp reminder is the approved template WHATSAPP_REMINDER_TEMPLATE
    (business, date, time, name), and Messenger and Instagram are skipped
    for the next messenger. The channel sender meters each delivery once.

    The booking is read again right before it is reminded and before it is
    marked, and only `reminder_sent_at` is changed on that fresh copy, so a
    cancellation or a move made meanwhile is never undone (and a booking
    cancelled or moved meanwhile is not reminded with stale details).

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
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        channel_message_sender: ChannelMessageSenderFacilitatorContract,
        reminder_transformer: TransformerContract[BookingMessageInput, MessageText],
        reminder_template_transformer: TransformerContract[
            BookingMessageInput, list[MessageText]
        ],
        wall_clock: WallClock[Microseconds],
        whatsapp_reminder_template: WhatsAppTemplateName | None = None,
        reminder_lead: BookingReminderLeadSeconds = DEFAULT_REMINDER_LEAD,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._channel_message_sender: ChannelMessageSenderFacilitatorContract = (
            channel_message_sender
        )
        self._reminder_transformer: TransformerContract[
            BookingMessageInput, MessageText
        ] = reminder_transformer
        self._reminder_template_transformer: TransformerContract[
            BookingMessageInput, list[MessageText]
        ] = reminder_template_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._whatsapp_reminder_template: WhatsAppTemplateName | None = (
            whatsapp_reminder_template
        )
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
            for due_booking in due_bookings:
                booking: BookingDocument | None = self._reread_if_still_due(
                    due_booking,
                    window_end_seconds,
                )
                if booking is not None and self._remind(
                    business, zone, cancellation_policy, booking
                ):
                    reminded += 1

        return JobReport(processed_count=ProcessedItemCount(reminded))

    def _reread_if_still_due(
        self,
        booking: BookingDocument,
        window_end_seconds: int,
    ) -> BookingDocument | None:
        """The booking as stored now, if it still needs this reminder."""

        current: BookingDocument | None = self._booking_repo.get(
            booking.business_id,
            booking.id,
        )
        now_seconds: int = microseconds_to_seconds(int(self._wall_clock.now_unix()))
        if current is None or not is_reminder_due(
            current, now_seconds, window_end_seconds
        ):
            return None

        return current

    def _remind(
        self,
        business: BusinessDocument,
        zone: ZoneInfo,
        cancellation_policy: CancellationPolicyText | None,
        booking: BookingDocument,
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
        message_input = BookingMessageInput(
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
        for identity in identities:
            try:
                if not self._deliver(business, contact, identity, message_input):
                    continue
            except ApplicationError as error:
                logger.warning(
                    "Reminder of booking %s through %s failed: %s",
                    booking.id,
                    identity.channel.value,
                    error,
                )
                continue

            self._mark_reminded(booking)
            return True

        return False

    def _deliver(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        identity: ChannelIdentity,
        message_input: BookingMessageInput,
    ) -> bool:
        """Send through one identity; False when that channel cannot carry it."""

        if identity.channel not in WINDOWED_CHANNELS or self._is_window_open(
            business, contact, identity.channel
        ):
            self._channel_message_sender.send(
                business.id,
                identity.channel,
                identity.channel_user_id,
                self._reminder_transformer.transform(message_input),
            )
            return True

        if (
            identity.channel is not ChannelKind.WHATSAPP
            or self._whatsapp_reminder_template is None
        ):
            logger.info(
                "Reminder through %s skipped: the customer wrote there more than "
                "24 hours ago%s.",
                identity.channel.value,
                (
                    " and WHATSAPP_REMINDER_TEMPLATE is not configured"
                    if identity.channel is ChannelKind.WHATSAPP
                    else ""
                ),
            )
            return False

        self._channel_message_sender.send_whatsapp_template(
            business.id,
            identity.channel_user_id,
            self._whatsapp_reminder_template,
            message_input.language,
            self._reminder_template_transformer.transform(message_input),
        )
        return True

    def _is_window_open(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        channel: ChannelKind,
    ) -> bool:
        """Did the customer write in this channel within the last 24 hours?"""

        window_start: int = int(self._wall_clock.now_unix()) - (
            CUSTOMER_SERVICE_WINDOW_SECONDS * MICROSECONDS_PER_SECOND
        )
        for conversation in self._conversation_repo.list_by_business(business.id):
            if (
                conversation.contact_id != contact.id
                or conversation.channel is not channel
                or conversation.is_sandbox
                or int(conversation.last_message_at) < window_start
            ):
                continue

            for message in self._message_repo.list_by_conversation(
                business.id, conversation.id
            ):
                if (
                    message.direction is MessageDirection.INBOUND
                    and int(message.created_at) >= window_start
                ):
                    return True

        return False

    def _mark_reminded(self, booking: BookingDocument) -> None:
        """
        Set only `reminder_sent_at` on the booking as stored now; a booking
        cancelled or moved during the send keeps that change.
        """

        current: BookingDocument | None = self._booking_repo.get(
            booking.business_id,
            booking.id,
        )
        if (
            current is None
            or current.status is not BookingStatus.CONFIRMED
            or current.starts_at != booking.starts_at
        ):
            return

        now: Microseconds = self._wall_clock.now_unix()
        current.reminder_sent_at = now
        current.updated_at = now
        self._booking_repo.save(current)

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
