"""A place a cancellation or a move gave up, as the waitlist's offer job reads it."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId


class FreedPlace(ImmutableDTO):
    """
    The resource and the time a booking gave up when it was cancelled or
    moved (its times before the move), and the booking itself.
    """

    freed_booking_id: BookingId
    resource_id: ResourceId
    starts_at: BookingStartsAtUnixSeconds
    ends_at: BookingEndsAtUnixSeconds
