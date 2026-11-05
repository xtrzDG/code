"""The queued job that offers a freed place to the waitlist, and its payload."""

from pydantic import ValidationError

from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.strings import JobPayloadJson

# A cancellation or a move freed a place: the first waiting customer who
# fits is offered it (`OfferFreedPlaceUseCase`).
OFFER_FREED_PLACE_JOB: JobName = JobName("offer_freed_place")
# Customers cancel or move for good; staff in the cabinet may undo a
# cancellation within seconds, so their freed places wait this long.
STAFF_CHANGE_DELAY_SECONDS: int = 120
MICROSECONDS_PER_SECOND: int = 1_000_000


def encode_freed_place(place: FreedPlace) -> JobPayloadJson:
    return JobPayloadJson(place.model_dump_json())


def decode_freed_place(payload: JobPayloadJson) -> FreedPlace:
    try:
        return FreedPlace.model_validate_json(str(payload))
    except ValidationError as error:
        raise ValidationFailedError(
            "The job payload does not name a freed place."
        ) from error


def waitlist_serial_key(business_id: BusinessId) -> JobSerialKey:
    """One business's freed places are offered one at a time, oldest first."""

    return JobSerialKey(f"waitlist:{business_id}")
