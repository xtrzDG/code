import logging

from typed_time_provider import Microseconds

from app.contracts.growth import GrowthBookingsFacilitatorContract
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.campaign_repositories import (
    CampaignMessageRepoContract,
)
from app.contracts.repositories.waitlist_repositories import (
    WaitlistEntryRepoContract,
    WaitlistSettingsRepoContract,
)
from app.schemas.constants.bookings import BookingOrigin
from app.schemas.constants.campaigns import CampaignMessageStatus, RebookingRuleKind
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.waitlist import WaitlistEndReason, WaitlistStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.campaigns import CampaignMessageDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument
from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.waitlist.booleans import (
    IsStaffBookingChange,
    IsWaitlistEnabled,
)
from app.utilities.waitlist.held_places import held_place_bookings
from app.utilities.waitlist.offer_jobs import (
    MICROSECONDS_PER_SECOND,
    OFFER_FREED_PLACE_JOB,
    STAFF_CHANGE_DELAY_SECONDS,
    encode_freed_place,
    waitlist_serial_key,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
# Offers held at once in one business: a handful in practice.
HELD_PLACES_LIMIT: DocumentQueryLimit = DocumentQueryLimit(500)
# A booking within a week of an invitation back counts for the campaign.
CAMPAIGN_ATTRIBUTION_SECONDS: int = 7 * 24 * 60 * 60
# Rules whose messages invite a customer to book (a pre-arrival note
# follows a booking that exists already).
INVITING_RULES: frozenset[RebookingRuleKind] = frozenset(
    {RebookingRuleKind.REBOOK, RebookingRuleKind.RECALL}
)


class GrowthBookingsFacilitator(GrowthBookingsFacilitatorContract):
    """
    The waitlist's and the campaigns' side of every booking change: the
    places held for waiting customers, the freed places queued for the
    offer job, and the revenue lines a new booking counts for.
    """

    def __init__(
        self,
        waitlist_entry_repo: WaitlistEntryRepoContract,
        waitlist_settings_repo: WaitlistSettingsRepoContract,
        campaign_message_repo: CampaignMessageRepoContract,
        job_queue: JobQueueFacilitatorContract,
    ) -> None:
        self._entries: WaitlistEntryRepoContract = waitlist_entry_repo
        self._settings: WaitlistSettingsRepoContract = waitlist_settings_repo
        self._messages: CampaignMessageRepoContract = campaign_message_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue

    def held_places(
        self,
        business_id: BusinessId,
        ends_after: BookingSearchBoundSeconds,
        now: Microseconds,
        holder: ContactId | None,
    ) -> list[BookingDocument]:
        return held_place_bookings(
            self._entries.list_in_status(
                business_id, WaitlistStatus.OFFERED, HELD_PLACES_LIMIT
            ),
            ends_after,
            now,
            holder,
        )

    def is_waitlist_open(self, business_id: BusinessId) -> IsWaitlistEnabled:
        settings = self._settings.get_by_business(business_id)
        return settings is None or settings.is_enabled

    def attribute(
        self, booking: BookingDocument, now: Microseconds
    ) -> BookingOrigin | None:
        if booking.is_sandbox:
            return None

        if self._claim_held_place(booking, now):
            return BookingOrigin.WAITLIST

        if self._credit_invitation(booking, now):
            return BookingOrigin.CAMPAIGN

        return None

    def notice_freed(
        self,
        booking: BookingDocument,
        place: FreedPlace,
        now: Microseconds,
        is_staff_change: IsStaffBookingChange = False,
    ) -> None:
        if booking.is_sandbox:
            return

        delay: int = STAFF_CHANGE_DELAY_SECONDS if is_staff_change else 0
        try:
            self._job_queue.enqueue(
                OFFER_FREED_PLACE_JOB,
                encode_freed_place(place),
                booking.business_id,
                run_at=Microseconds(int(now) + delay * MICROSECONDS_PER_SECOND),
                lane=JobLane.DEFAULT,
                serial_key=waitlist_serial_key(booking.business_id),
            )
        except Exception:
            LOGGER.exception(
                "The freed place of booking %s was not queued for the waitlist.",
                booking.id,
            )

    def _claim_held_place(self, booking: BookingDocument, now: Microseconds) -> bool:
        """The customer's offered place (held, or lapsed unanswered) is now theirs."""

        for entry in self._entries.list_of_contact(
            booking.business_id, booking.contact_id
        ):
            if not takes_offered_place(entry, booking):
                continue

            def book(current: WaitlistEntryDocument) -> WaitlistEntryDocument | None:
                if not takes_offered_place(current, booking):
                    return None

                current.status = WaitlistStatus.BOOKED
                current.booking_id = booking.id
                current.booked_at = now
                current.offer_expires_at = None
                current.end_reason = None
                current.ended_at = None
                current.updated_at = now
                return current

            if self._entries.update(booking.business_id, entry.id, book) is not None:
                return True

        return False

    def _credit_invitation(self, booking: BookingDocument, now: Microseconds) -> bool:
        """The customer's latest invitation of the last week led to this booking."""

        since: int = int(now) - CAMPAIGN_ATTRIBUTION_SECONDS * MICROSECONDS_PER_SECOND
        invitations: list[CampaignMessageDocument] = sorted(
            (
                message
                for message in self._messages.list_of_contact(
                    booking.business_id, booking.contact_id
                )
                if message.status is CampaignMessageStatus.SENT
                and message.rule_kind in INVITING_RULES
                and message.sent_at is not None
                and int(message.sent_at) >= since
            ),
            key=lambda message: int(message.sent_at or 0),
            reverse=True,
        )
        for invitation in invitations:

            def credit(
                current: CampaignMessageDocument,
            ) -> CampaignMessageDocument | None:
                if current.status is not CampaignMessageStatus.SENT:
                    return None

                current.status = CampaignMessageStatus.BOOKED
                current.booking_id = booking.id
                current.booked_at = now
                current.updated_at = now
                return current

            if (
                self._messages.update(booking.business_id, invitation.id, credit)
                is not None
            ):
                return True

        return False


def takes_offered_place(entry: WaitlistEntryDocument, booking: BookingDocument) -> bool:
    """
    The booking is the place offered to the entry: the same resource and
    start, while the offer is held or after it lapsed without an answer.
    """

    offer = entry.offer
    if offer is None or offer.resource_id != booking.resource_id:
        return False

    if int(offer.starts_at) != int(booking.starts_at):
        return False

    return entry.status is WaitlistStatus.OFFERED or (
        entry.status is WaitlistStatus.EXPIRED
        and entry.end_reason is WaitlistEndReason.NO_ANSWER
    )
