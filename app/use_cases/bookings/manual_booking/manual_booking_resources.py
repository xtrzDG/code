"""The offer and resources a manual booking may use."""

from collections.abc import Sequence
from typing import NamedTuple

from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.operations.bookings import ManualBookingCommand
from app.use_cases.bookings.booking_support import SchedulingInputs
from app.use_cases.bookings.offer_selection import (
    OfferChoice,
    OfferRequest,
    choose_offer,
    require_seating,
)


class ManualPlacement(NamedTuple):
    """The offer of a manual booking and the resources that seat its party."""

    choice: OfferChoice
    candidates: list[ResourceDocument]


def choose_seating_candidates(
    inputs: SchedulingInputs,
    items: Sequence[KnowledgeItemDocument],
    command: ManualBookingCommand,
) -> ManualPlacement:
    """
    The service (if any) with its performers, else the requested resource
    or kind, keeping those that seat the party, best fit first. Staff may
    book a service for another length than its usual one.

    Raises:
        ValidationFailedError: none seats the party (NO_SEATING_RESOURCE),
            or the resource does not perform the service (NOT_PERFORMED).
        NotFoundError: no such active service or resource.
    """

    choice: OfferChoice = choose_offer(
        inputs,
        items,
        OfferRequest(
            service_item_id=command.service_item_id,
            resource_id=command.resource_id,
            resource_kind=command.resource_kind,
            duration_minutes=command.duration_minutes,
            is_duration_override_allowed=True,
        ),
    )
    return ManualPlacement(
        choice=choice,
        candidates=require_seating(choice.candidates, command.party_size, ""),
    )
