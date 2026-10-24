"""Giving a rented number back: the state change both its triggers make."""

from typed_time_provider import Microseconds

from app.schemas.constants.phone_numbers import (
    PhoneNumberReleaseReason,
    PhoneNumberStatus,
)
from app.schemas.domain.phone_numbers import PhoneNumberDocument


def mark_releasing(
    number: PhoneNumberDocument,
    reason: PhoneNumberReleaseReason,
    now: Microseconds,
) -> PhoneNumberDocument | None:
    """
    An ACTIVE number to give back, with why and when (None: it is not
    active any more, so nothing changes).
    """

    if number.status is not PhoneNumberStatus.ACTIVE:
        return None

    return number.model_copy(
        update={
            "status": PhoneNumberStatus.RELEASING,
            "release_reason": reason,
            "release_requested_at": now,
            "updated_at": now,
        }
    )
