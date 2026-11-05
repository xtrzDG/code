"""
Which offer and resources a booking request means, and what the booking
is then worth: the steps the assistant's and the cabinet's bookings share.

A request may name a service (an id or a name in any script) and a
resource (likewise): "a 45-minute haircut with Nino". The service sets
the length of the visit and the buffer after it, and only its performers
are candidates; a named resource must be one of them. Without a service
the request books as before (a resource, a kind, or the usual kind).
"""

from collections.abc import Sequence
from datetime import date
from typing import NamedTuple

from app.schemas.constants.bookings import BookingRefusalCode, ResourceKind
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookable_offers import BookingPrice
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    BookingValueMinor,
    NightCount,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.bookings.strings import ResourceReference
from app.schemas.typings.knowledge.constrained_integers import BufferMinutes
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import ServiceReference
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.use_cases.bookings.booking_support import SchedulingInputs
from app.utilities.bookings.bookable_offers import (
    buffer_of_offer,
    is_bookable_item,
    performers_of,
)
from app.utilities.bookings.booking_values import offer_of_booking, price_booking
from app.utilities.bookings.target_resolution import resolve_resource, resolve_service
from app.utilities.scheduling.placement import Placement
from app.utilities.scheduling.placement_errors import booking_refusal_reason
from app.utilities.scheduling.resource_selection import (
    seating_resources,
    select_resources,
)


class OfferRequest(NamedTuple):
    """What a booking request names (each part optional)."""

    service_reference: ServiceReference | None = None
    service_item_id: KnowledgeItemId | None = None
    resource_reference: ResourceReference | None = None
    resource_id: ResourceId | None = None
    resource_kind: ResourceKind | None = None
    duration_minutes: BookingDurationMinutes | None = None
    # Staff may book a service for longer or shorter than its usual length;
    # the assistant always books its full length.
    is_duration_override_allowed: bool = False


class OfferChoice(NamedTuple):
    """The offer of a request and where and how long it may be booked."""

    offer: KnowledgeItemDocument | None
    candidates: list[ResourceDocument]
    duration_minutes: BookingDurationMinutes | None
    buffer_minutes: BufferMinutes | None


def choose_offer(
    inputs: SchedulingInputs,
    items: Sequence[KnowledgeItemDocument],
    request: OfferRequest,
) -> OfferChoice:
    """
    The offer and its candidate resources (see the module).

    Raises:
        ValidationFailedError: an unknown or ambiguous service or resource
            name, or a resource that does not perform the service.
        NotFoundError: an id of no active service or resource.
    """

    offer: KnowledgeItemDocument | None = find_offer(items, request)
    resource_id: ResourceId | None = request.resource_id
    if request.resource_reference is not None:
        resource_id = resolve_resource(request.resource_reference, inputs.resources).id

    if offer is None:
        return OfferChoice(
            offer=None,
            candidates=select_resources(
                inputs.resources, resource_id, request.resource_kind, inputs.rules
            ),
            duration_minutes=request.duration_minutes,
            buffer_minutes=None,
        )

    performers: list[ResourceDocument] = performers_of(offer, inputs.resources, items)
    if resource_id is not None:
        chosen: ResourceDocument = select_resources(
            inputs.resources, resource_id, None, inputs.rules
        )[0]
        if chosen.id not in {performer.id for performer in performers}:
            raise not_performed_error(offer, chosen, performers)

        performers = [chosen]

    if not performers:
        raise not_performed_error(offer, None, performers)

    return OfferChoice(
        offer=offer,
        candidates=performers,
        duration_minutes=offer_duration(offer, request),
        buffer_minutes=buffer_of_offer(offer),
    )


def find_offer(
    items: Sequence[KnowledgeItemDocument],
    request: OfferRequest,
) -> KnowledgeItemDocument | None:
    if request.service_reference is not None:
        return resolve_service(request.service_reference, items)

    if request.service_item_id is None:
        return None

    for item in items:
        if item.id == request.service_item_id and is_bookable_item(item):
            return item

    raise NotFoundError(f"Service {request.service_item_id} was not found.")


def offer_duration(
    offer: KnowledgeItemDocument,
    request: OfferRequest,
) -> BookingDurationMinutes | None:
    """The offer's length, unless staff asked for another one."""

    if request.duration_minutes is not None and (
        request.is_duration_override_allowed or offer.duration_minutes is None
    ):
        return request.duration_minutes

    if offer.duration_minutes is None:
        return None

    return BookingDurationMinutes(int(offer.duration_minutes))


def not_performed_error(
    offer: KnowledgeItemDocument,
    chosen: ResourceDocument | None,
    performers: Sequence[ResourceDocument],
) -> ValidationFailedError:
    names: list[str] = [str(performer.name) for performer in performers]
    who: str = (
        f"It is done by: {', '.join(names)}."
        if names
        else "Nobody can take it at the moment; pass the request to a manager."
    )
    subject: str = "" if chosen is None else f"{chosen.name} does not do this. "
    message: str = f"{subject}{offer.title}: {who}"
    return ValidationFailedError(
        message,
        reasons=[
            booking_refusal_reason(
                BookingRefusalCode.NOT_PERFORMED,
                message,
                [str(offer.id), *(str(performer.id) for performer in performers)],
            )
        ],
    )


def require_seating(
    candidates: Sequence[ResourceDocument],
    party_size: PartySize,
    advice: str,
) -> list[ResourceDocument]:
    """
    The candidates that seat the party, best fit first.

    Raises:
        ValidationFailedError: none does (reason NO_SEATING_RESOURCE).
    """

    seating: list[ResourceDocument] = seating_resources(candidates, party_size)
    if seating:
        return seating

    message: str = f"No bookable resource seats {int(party_size)} guests{advice}."
    raise ValidationFailedError(
        message,
        reasons=[
            booking_refusal_reason(
                BookingRefusalCode.NO_SEATING_RESOURCE,
                message,
                [str(int(party_size))],
            )
        ],
    )


class BookedOffer(NamedTuple):
    """What a placed booking records about its offer and value."""

    offer: KnowledgeItemDocument | None
    price: BookingPrice | None

    @property
    def service_item_id(self) -> KnowledgeItemId | None:
        return None if self.offer is None else self.offer.id

    @property
    def value_minor(self) -> BookingValueMinor | None:
        return None if self.price is None else self.price.value_minor

    @property
    def currency_code(self) -> CurrencyCode | None:
        return None if self.price is None else self.price.currency_code


def price_placement(
    choice: OfferChoice,
    placement: Placement,
    items: Sequence[KnowledgeItemDocument],
    local_date: date,
    nights: NightCount | None,
    inputs: SchedulingInputs,
) -> BookedOffer:
    """The booked offer (a room's room type when none was named) and its value."""

    offer: KnowledgeItemDocument | None = offer_of_booking(
        choice.offer, placement.resource, items
    )
    return BookedOffer(
        offer=offer,
        price=price_booking(
            offer,
            placement.resource.booking_unit,
            local_date,
            nights,
            inputs.business.currency_code,
        ),
    )
