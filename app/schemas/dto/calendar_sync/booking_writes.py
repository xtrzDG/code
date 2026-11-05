"""The queued writes of the platform's bookings to booking systems."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class BookingSystemWriteJob(ImmutableDTO):
    """
    The payload of a `write_booking_system_booking` job: the booking whose
    current state its resource's booking system should show.
    """

    business_id: BusinessId
    booking_id: BookingId
