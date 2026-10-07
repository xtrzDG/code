"""
Holding a freed place for one waiting customer: whether the place is still
free (no booking, no other hold and no busy time of a calendar outside the
platform takes its unit), how long the hold may
last (the business's hold, ending before the online-booking notice of the
place's start), and the entry's step from WAITING to OFFERED.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.waitlist import WaitlistStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.profiles import BookingRules
from app.schemas.domain.resources import ResourceDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistOffer
from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.waitlist.constrained_integers import (
    WaitlistHoldMinutes,
    WaitlistOfferCount,
)
from app.utilities.scheduling.availability import busy_ranges
from app.utilities.scheduling.overlap import BlockedTime, has_free_unit
from app.utilities.scheduling.resource_selection import min_notice_seconds
from app.utilities.waitlist.held_places import held_place_bookings

MICROSECONDS_PER_SECOND: int = 1_000_000
SECONDS_PER_MINUTE: int = 60
# A hold shorter than this gives the customer no real chance to answer.
MIN_HOLD_SECONDS: int = 5 * 60
# The longest buffer a booking keeps after its end (BufferMinutes.le).
LONGEST_BUFFER_SECONDS: int = 24 * 60 * 60
# Offers held at once in one business: a handful in practice.
HOLDS_LIMIT: DocumentQueryLimit = DocumentQueryLimit(500)


def hold_ends_at(
    place: FreedPlace,
    hold_minutes: WaitlistHoldMinutes,
    rules: BookingRules | None,
    now: Microseconds,
) -> Microseconds | None:
    """When the hold ends; None when too little time is left to offer the place."""

    latest: int = (int(place.starts_at) - min_notice_seconds(rules)) * (
        MICROSECONDS_PER_SECOND
    )
    ends: int = min(
        int(now) + int(hold_minutes) * SECONDS_PER_MINUTE * MICROSECONDS_PER_SECOND,
        latest,
    )
    if ends - int(now) < MIN_HOLD_SECONDS * MICROSECONDS_PER_SECOND:
        return None

    return Microseconds(ends)


def is_place_free(
    booking_repo: BookingRepoContract,
    entry_repo: WaitlistEntryRepoContract,
    place: FreedPlace,
    resource: ResourceDocument,
    buffer_seconds: int,
    now: Microseconds,
    blocked_times: Sequence[BlockedTime] = (),
) -> bool:
    """
    No booking and no live hold takes the place's unit, and no calendar
    outside the platform made the resource busy then (`blocked_times`, as
    availability reads them), under the lock.
    """

    business_id: BusinessId = resource.business_id
    bound = BookingSearchBoundSeconds(
        max(int(place.starts_at) - LONGEST_BUFFER_SECONDS, 0)
    )
    taken: Sequence[BookingDocument] = [
        *booking_repo.list_ending_after(business_id, bound),
        *held_place_bookings(
            entry_repo.list_in_status(business_id, WaitlistStatus.OFFERED, HOLDS_LIMIT),
            bound,
            now,
            None,
        ),
    ]
    return has_free_unit(
        busy_ranges(
            taken, resource, include_sandbox=False, blocked_times=blocked_times
        ),
        int(place.starts_at),
        int(place.ends_at) + buffer_seconds,
        int(resource.unit_count),
    )


def hold_for(
    entry_repo: WaitlistEntryRepoContract,
    entry: WaitlistEntryDocument,
    offer: WaitlistOffer,
    expires_at: Microseconds,
    channel: ChannelKind,
) -> WaitlistEntryDocument | None:
    """The entry, still waiting, now OFFERED the place; None when it moved on."""

    def hold(current: WaitlistEntryDocument) -> WaitlistEntryDocument | None:
        if current.status is not WaitlistStatus.WAITING:
            return None

        current.status = WaitlistStatus.OFFERED
        current.offer = offer.model_copy(update={"channel": channel})
        current.offer_expires_at = expires_at
        current.offer_count = WaitlistOfferCount(int(current.offer_count) + 1)
        current.updated_at = offer.offered_at
        return current

    return entry_repo.update(entry.business_id, entry.id, hold)
