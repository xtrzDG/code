import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingConfirmationChange
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversation_engine import TurnGate
from app.schemas.constants.feedback import CustomerSignalKind
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.waitlist import (
    WaitlistAnswer,
    WaitlistEndReason,
    WaitlistStatus,
)
from app.schemas.domain.waitlist import WaitlistEntryDocument
from app.schemas.dto.booking_manage import (
    BookingConfirmationReceipt,
    BookingConfirmationRequest,
)
from app.schemas.dto.bookings import BookingResult, CreateBookingCommand
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.feedback.customer_signals import CustomerSignalReply
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.waitlist.offer_answering import booking_of_offer
from app.use_cases.waitlist.waitlist_release import queue_next_offer
from app.utilities.scheduling.zoned_time import load_time_zone
from app.utilities.waitlist.offer_answers import read_offer_answer
from app.utilities.waitlist.waitlist_reply_texts import (
    OFFER_DECLINED_TEXT,
    OFFER_GONE_TEXT,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000


class AnswerWaitlistOfferUseCase(
    UseCaseContract[PreparedTurn, CustomerSignalReply | None]
):
    """
    A customer's yes or no to the place the waitlist offered them, answered
    by the platform before the assistant (the whole message is the answer,
    in any of the offer's languages, and nothing was written to them since
    the offer). None for every other message: the assistant answers it, and
    sees the offer in the conversation.

    "Yes" books exactly the offered place under the business's booking lock
    (the booking use case finds the hold is theirs, marks the entry BOOKED
    and the booking as the waitlist's), confirms it in writing and answers
    with the confirmation. A late "yes" after the hold ran out still books
    the place while nobody else took it; otherwise the customer hears so and
    waits on. "No" lets the place go to the next customer who fits.
    """

    def __init__(
        self,
        waitlist_entry_repo: WaitlistEntryRepoContract,
        message_repo: MessageRepoContract,
        resource_repo: ResourceRepoContract,
        create_booking: UseCaseContract[CreateBookingCommand, BookingResult],
        send_confirmation: UseCaseContract[
            BookingConfirmationRequest, BookingConfirmationReceipt
        ],
        job_queue: JobQueueFacilitatorContract,
        text_resolver: LocalizedTextResolverContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._entry_repo: WaitlistEntryRepoContract = waitlist_entry_repo
        self._message_repo: MessageRepoContract = message_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._create_booking: UseCaseContract[CreateBookingCommand, BookingResult] = (
            create_booking
        )
        self._send_confirmation: UseCaseContract[
            BookingConfirmationRequest, BookingConfirmationReceipt
        ] = send_confirmation
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PreparedTurn) -> CustomerSignalReply | None:
        if input_data.conversation.is_sandbox or input_data.gate is (
            TurnGate.BLOCKED_SILENCE
        ):
            return None

        answer: WaitlistAnswer | None = read_offer_answer(str(input_data.customer_text))
        if answer is None:
            return None

        now: Microseconds = self._wall_clock.now_unix()
        entry: WaitlistEntryDocument | None = self._answered_entry(input_data, now)
        if entry is None:
            return None

        if answer is WaitlistAnswer.YES:
            return self._take(input_data, entry, now)

        return self._decline(input_data, entry, now)

    def _answered_entry(
        self, turn: PreparedTurn, now: Microseconds
    ) -> WaitlistEntryDocument | None:
        """The newest offer in this conversation the message answers."""

        offered = sorted(
            (
                entry
                for entry in self._entry_repo.list_of_contact(
                    turn.business.id, turn.contact.id
                )
                if is_answerable(entry, turn, now)
            ),
            key=lambda entry: int(entry.offer.offered_at if entry.offer else 0),
            reverse=True,
        )
        for entry in offered[:1]:
            if entry.offer is None:
                return None

            written_since = self._message_repo.count_by_conversation(
                turn.business.id,
                turn.conversation.id,
                MessageDirection.OUTBOUND,
                created_from=Microseconds(int(entry.offer.offered_at) + 1),
            )
            return entry if int(written_since) == 0 else None

        return None

    def _take(
        self, turn: PreparedTurn, entry: WaitlistEntryDocument, now: Microseconds
    ) -> CustomerSignalReply | None:
        offer = entry.offer
        resource = (
            None
            if offer is None
            else self._resource_repo.get(turn.business.id, offer.resource_id)
        )
        if offer is None or resource is None:
            return None

        command = booking_of_offer(
            turn, entry, offer, resource, load_time_zone(turn.business.timezone)
        )
        if command is None:
            return None

        try:
            result: BookingResult = self._create_booking.run(command)
        except ApplicationError:
            self._wait_on(entry, now)
            return self._reply(turn, OFFER_GONE_TEXT)

        self._confirm(turn, result)
        self._live_events.publish(
            turn.business.id, LiveEventKind.WAITLIST_CHANGED, (entry.id,)
        )
        return CustomerSignalReply(
            kind=CustomerSignalKind.WAITLIST_ANSWER,
            text=result.confirmation_text,
            booking_id=result.booking.id,
        )

    def _decline(
        self, turn: PreparedTurn, entry: WaitlistEntryDocument, now: Microseconds
    ) -> CustomerSignalReply:
        def decline(current: WaitlistEntryDocument) -> WaitlistEntryDocument | None:
            if current.status is not WaitlistStatus.OFFERED:
                return None

            current.status = WaitlistStatus.EXPIRED
            current.end_reason = WaitlistEndReason.DECLINED
            current.offer_expires_at = None
            current.ended_at = now
            current.updated_at = now
            return current

        declined = self._entry_repo.update(turn.business.id, entry.id, decline)
        if declined is not None:
            queue_next_offer(self._job_queue, declined, now)
            self._live_events.publish(
                turn.business.id, LiveEventKind.WAITLIST_CHANGED, (entry.id,)
            )

        return self._reply(turn, OFFER_DECLINED_TEXT)

    def _wait_on(self, entry: WaitlistEntryDocument, now: Microseconds) -> None:
        """The place is gone: the customer waits on (while a place can still come)."""

        def back(current: WaitlistEntryDocument) -> WaitlistEntryDocument | None:
            if current.status is WaitlistStatus.BOOKED or int(
                current.waits_until
            ) <= int(now):
                return None

            current.status = WaitlistStatus.WAITING
            current.offer = None
            current.offer_expires_at = None
            current.end_reason = None
            current.ended_at = None
            current.updated_at = now
            return current

        if self._entry_repo.update(entry.business_id, entry.id, back) is not None:
            self._live_events.publish(
                entry.business_id, LiveEventKind.WAITLIST_CHANGED, (entry.id,)
            )

    def _confirm(self, turn: PreparedTurn, result: BookingResult) -> None:
        try:
            self._send_confirmation.run(
                BookingConfirmationRequest(
                    business_id=turn.business.id,
                    booking_id=result.booking.id,
                    change=BookingConfirmationChange.BOOKED,
                    language=turn.reply_language,
                )
            )
        except Exception:
            LOGGER.exception(
                "The confirmation of booking %s was not sent.", result.booking.id
            )

    def _reply(self, turn: PreparedTurn, text: LocalizedText) -> CustomerSignalReply:
        return CustomerSignalReply(
            kind=CustomerSignalKind.WAITLIST_ANSWER,
            text=MessageText(self._text_resolver.resolve(text, turn.reply_language)),
        )


def is_answerable(
    entry: WaitlistEntryDocument, turn: PreparedTurn, now: Microseconds
) -> bool:
    """
    An offer made in this conversation, still held or lapsed unanswered,
    whose place has not started yet.
    """

    offer = entry.offer
    if offer is None or offer.conversation_id != turn.conversation.id:
        return False

    if int(offer.starts_at) * MICROSECONDS_PER_SECOND <= int(now):
        return False

    return entry.status is WaitlistStatus.OFFERED or (
        entry.status is WaitlistStatus.EXPIRED
        and entry.end_reason is WaitlistEndReason.NO_ANSWER
    )
