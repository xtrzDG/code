"""
A held place given back (declined, unanswered, the customer taken off the
list) goes to the next waiting customer who fits: the offer job is queued
again for the same freed place.
"""

from typed_time_provider import Microseconds

from app.contracts.jobs import JobQueueFacilitatorContract
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.waitlist import WaitlistEntryDocument
from app.schemas.dto.growth.freed_places import FreedPlace
from app.utilities.waitlist.offer_jobs import (
    OFFER_FREED_PLACE_JOB,
    encode_freed_place,
    waitlist_serial_key,
)


def queue_next_offer(
    job_queue: JobQueueFacilitatorContract,
    entry: WaitlistEntryDocument,
    now: Microseconds,
) -> None:
    """Offer the entry's place to the next customer (nothing when it held none)."""

    offer = entry.offer
    if offer is None:
        return

    job_queue.enqueue(
        OFFER_FREED_PLACE_JOB,
        encode_freed_place(
            FreedPlace(
                freed_booking_id=offer.freed_booking_id,
                resource_id=offer.resource_id,
                starts_at=offer.starts_at,
                ends_at=offer.ends_at,
            )
        ),
        entry.business_id,
        run_at=now,
        lane=JobLane.DEFAULT,
        serial_key=waitlist_serial_key(entry.business_id),
    )
