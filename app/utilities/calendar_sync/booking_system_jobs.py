"""
The `write_booking_system_booking` job: its name, payload and serial key
(the writes of one booking run one at a time, in the order of its changes).
"""

from pydantic import ValidationError

from app.schemas.dto.calendar_sync.booking_writes import BookingSystemWriteJob
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.strings import JobPayloadJson

# A booking written to (or cancelled in) its resource's booking system.
WRITE_BOOKING_SYSTEM_BOOKING_JOB: JobName = JobName("write_booking_system_booking")


def encode_booking_system_write(
    business_id: BusinessId, booking_id: BookingId
) -> JobPayloadJson:
    return JobPayloadJson(
        BookingSystemWriteJob(
            business_id=business_id, booking_id=booking_id
        ).model_dump_json()
    )


def decode_booking_system_write(payload: JobPayloadJson) -> BookingSystemWriteJob:
    try:
        return BookingSystemWriteJob.model_validate_json(str(payload))
    except ValidationError as error:
        raise ValidationFailedError(
            "The job payload does not name a booking to write."
        ) from error


def booking_system_write_key(booking_id: BookingId) -> JobSerialKey:
    return JobSerialKey(f"booking_system:{booking_id}")
