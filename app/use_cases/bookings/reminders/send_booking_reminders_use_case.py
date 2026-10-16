"""Background job: remind customers of their bookings the day before."""

import logging
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.privacy import SuppressionListContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingStatus
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
from app.use_cases.bookings.reminders.reminder_delivery import ReminderDelivery
from app.use_cases.bookings.reminders.reminder_rules import (
    build_reminder_message,
    choose_reminder_identities,
    is_reminder_due,
    read_cancellation_policy,
    sends_reminders,
)
from app.use_cases.shared.business_walk import walk_businesses
from app.utilities.channels.proactive_limits import (
    PROACTIVE_WINDOW,
    proactive_message_counter,
)
from app.utilities.privacy.messaging_suppression import is_messaging_suppressed
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
    for the next messenger; so is a messenger the business no longer has
    connected. The reminder goes into the outbox, once per booking and
    start time (a run after a crash finds it queued instead of sending it
    twice), and the worker sends it with retries; each delivery is metered
    once.

    A customer who opted out of unrequested messages (STOP, also as a
    suppression-list entry that outlived an erasure) gets no reminder, and
    every reminder counts against the customer's shared daily cap of such
    messages.

    The booking is read again right before it is reminded and before it is
    marked, and only `reminder_sent_at` is changed on that fresh copy, so a
    cancellation or a move made meanwhile is never undone (and a booking
    cancelled or moved meanwhile is not reminded with stale details).

    A booking whose reminder could not be queued (an error, or no channel
    can carry it) stays unreminded, so the next run tries again until the
    booking starts. Businesses the owner
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
        channel_repo: ChannelRepoContract,
        outbound_message_repo: OutboundMessageRepoContract,
        job_queue: JobQueueFacilitatorContract,
        reminder_transformer: TransformerContract[BookingMessageInput, MessageText],
        reminder_template_transformer: TransformerContract[
            BookingMessageInput, list[MessageText]
        ],
        wall_clock: WallClock[Microseconds],
        rate_limits: RequestRateLimitRegistryContract,
        suppression_list: SuppressionListContract,
        whatsapp_reminder_template: WhatsAppTemplateName | None = None,
        reminder_lead: BookingReminderLeadSeconds = DEFAULT_REMINDER_LEAD,
        unit_of_work: StorageUnitOfWorkContract | None = None,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._delivery: ReminderDelivery = ReminderDelivery(
            conversation_repo=conversation_repo,
            message_repo=message_repo,
            channel_repo=channel_repo,
            outbound_message_repo=outbound_message_repo,
            job_queue=job_queue,
            unit_of_work=unit_of_work,
            reminder_transformer=reminder_transformer,
            reminder_template_transformer=reminder_template_transformer,
            wall_clock=wall_clock,
            whatsapp_reminder_template=whatsapp_reminder_template,
        )
        self._rate_limits: RequestRateLimitRegistryContract = rate_limits
        self._suppression_list: SuppressionListContract = suppression_list
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._reminder_lead: BookingReminderLeadSeconds = reminder_lead

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        now_seconds: int = microseconds_to_seconds(int(now))
        window_end_seconds: int = now_seconds + int(self._reminder_lead)
        reminded: int = 0
        for business in walk_businesses(self._business_repo):
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
        if self._delivery.is_queued(booking):
            self._mark_reminded(booking)
            return True

        contact: ContactDocument | None = self._contact_repo.get(
            business.id,
            booking.contact_id,
        )
        if contact is None or is_messaging_suppressed(
            self._suppression_list, business.id, contact
        ):
            return False

        identities: list[ChannelIdentity] = choose_reminder_identities(
            contact,
            booking.source_channel,
        )
        if not identities or not self._within_daily_cap(business, contact):
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
                if not self._delivery.deliver(
                    business, contact, identity, booking, message_input
                ):
                    continue
            except ApplicationError as error:
                logger.warning(
                    "Reminder of booking %s through %s was not queued: %s",
                    booking.id,
                    identity.channel.value,
                    error,
                )
                return False

            self._mark_reminded(booking)
            return True

        return False

    def _within_daily_cap(
        self, business: BusinessDocument, contact: ContactDocument
    ) -> bool:
        """The customer's shared daily cap of unrequested messages allows one."""

        refused = self._rate_limits.try_acquire_all(
            [proactive_message_counter(business.id, contact.id)],
            PROACTIVE_WINDOW,
            self._wall_clock.now_unix(),
        )
        if refused is not None:
            logger.info(
                "Reminder to contact %s skipped: the daily cap of messages is used.",
                contact.id,
            )

        return refused is None

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
