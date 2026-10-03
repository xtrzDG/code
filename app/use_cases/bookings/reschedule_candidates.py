"""Where a moved booking may go: its own resource first, then same-kind ones."""

from collections.abc import Sequence

from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.resources import ResourceDocument
from app.utilities.scheduling.resource_selection import seating_resources


def reschedule_candidates(
    resources: Sequence[ResourceDocument],
    booking: BookingDocument,
    current: ResourceDocument,
) -> list[ResourceDocument]:
    """The booked resource first (if active), then same-kind alternatives."""

    alternatives: list[ResourceDocument] = seating_resources(
        [
            resource
            for resource in resources
            if resource.is_active
            and resource.id != current.id
            and resource.kind is current.kind
            and resource.booking_unit is current.booking_unit
        ],
        booking.party_size,
    )
    if not current.is_active:
        return alternatives

    return [current, *alternatives]
