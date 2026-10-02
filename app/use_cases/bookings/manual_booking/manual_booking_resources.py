"""The resources a manual booking may use."""

from app.schemas.constants.bookings import BookingRefusalCode
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.operations.bookings import ManualBookingCommand
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.use_cases.bookings.booking_support import SchedulingInputs
from app.utilities.scheduling.placement_errors import booking_refusal_reason
from app.utilities.scheduling.resource_selection import (
    seating_resources,
    select_resources,
)


def choose_seating_candidates(
    inputs: SchedulingInputs,
    command: ManualBookingCommand,
) -> list[ResourceDocument]:
    """
    The resources that seat the party, best fit first.

    Raises:
        ValidationFailedError: none does (reason NO_SEATING_RESOURCE).
    """

    candidates: list[ResourceDocument] = seating_resources(
        select_resources(
            inputs.resources,
            command.resource_id,
            command.resource_kind,
            inputs.rules,
        ),
        command.party_size,
    )
    if not candidates:
        message: str = f"No bookable resource seats {int(command.party_size)} guests."
        raise ValidationFailedError(
            message,
            reasons=[
                booking_refusal_reason(
                    BookingRefusalCode.NO_SEATING_RESOURCE,
                    message,
                    [str(int(command.party_size))],
                )
            ],
        )

    return candidates
