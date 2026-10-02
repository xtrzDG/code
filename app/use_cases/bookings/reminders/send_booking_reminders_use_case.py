"""Background job: remind customers of their bookings the day before."""

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
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.operations.message_texts import BookingMessageInput
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.bookings.constrained_integers import BookingReminderLeadSeconds
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.profiles.strings import CancellationPolicyText
from app.use_cases.bookings.reminders.messaging_window import (
    WINDOWED_CHANNELS,
    is_messaging_window_open,
)
from app.use_cases.bookings.reminders.reminder_rules import (
    build_reminder_message,
    choose_reminder_identities,
    is_reminder_due,
    read_cancellation_policy,
    sends_reminders,
)
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
)

logger: logging.Logger = logging.getLogger(__name__)
# The concept's reminder goes out the day before (configurable per process).
DEFAULT_REMINDER_LEAD: BookingReminderLeadSeconds = BookingReminderLeadSeconds(
    24 * 60 * 60
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
                read_cancellation_policy(self._business_profile_repo, business)
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
        message_input: BookingMessageInput = build_reminder_message(
            business, zone, cancellation_policy, booking, resource, contact
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

        if identity.channel not in WINDOWED_CHANNELS or is_messaging_window_open(
            self._conversation_repo,
            self._message_repo,
            business,
            contact,
            identity.channel,
            self._wall_clock.now_unix(),
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
