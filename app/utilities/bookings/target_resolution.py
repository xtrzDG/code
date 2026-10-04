"""
The service and the resource a booking request names, by id or by a name
written in any script ("Nino", "ნინო", "Нино"; "стрижку").

An unknown or ambiguous name is refused with a message the model acts on
(it lists what exists, so the model can ask the customer) and a reason
code the cabinet translates.
"""

from collections.abc import Sequence

from app.schemas.constants.bookings import BookingRefusalCode
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.bookings.bookable_offers import bookable_offers
from app.utilities.bookings.name_matching import NameMatch, best_name_matches
from app.utilities.scheduling.placement_errors import booking_refusal_reason

MAX_LISTED_OPTIONS: int = 12


def resolve_service(
    reference: str,
    items: Sequence[KnowledgeItemDocument],
) -> KnowledgeItemDocument:
    """
    The active service, package or room type with this id, else the one
    whose title matches best.

    Raises:
        ValidationFailedError: none matches (UNKNOWN_SERVICE), or several
            match equally well (AMBIGUOUS_SERVICE).
    """

    offers: list[KnowledgeItemDocument] = bookable_offers(items)
    wanted: str = reference.strip()
    for offer in offers:
        if str(offer.id) == wanted:
            return offer

    matches: list[NameMatch[KnowledgeItemDocument]] = best_name_matches(
        wanted, [(offer, str(offer.title)) for offer in offers]
    )
    if len(matches) == 1:
        return matches[0].item

    if matches:
        names: list[str] = [describe(match.item) for match in matches]
        message: str = (
            f'"{wanted}" matches several services: {"; ".join(names)}. Ask the '
            "customer which one they mean."
        )
        raise ValidationFailedError(
            message,
            reasons=[
                booking_refusal_reason(
                    BookingRefusalCode.AMBIGUOUS_SERVICE, message, names
                )
            ],
        )

    available: list[str] = [describe(offer) for offer in offers[:MAX_LISTED_OPTIONS]]
    message = f'No bookable service matches "{wanted}". ' + (
        f"Bookable services: {'; '.join(available)}."
        if available
        else "The business has no bookable services."
    )
    raise ValidationFailedError(
        message,
        reasons=[
            booking_refusal_reason(
                BookingRefusalCode.UNKNOWN_SERVICE, message, [wanted]
            )
        ],
    )


def resolve_resource(
    reference: str,
    resources: Sequence[ResourceDocument],
) -> ResourceDocument:
    """
    The active resource with this id, else the one whose name matches best.

    Raises:
        ValidationFailedError: none matches (UNKNOWN_RESOURCE), or several
            match equally well (AMBIGUOUS_RESOURCE).
    """

    active: list[ResourceDocument] = sorted(
        (resource for resource in resources if resource.is_active),
        key=lambda resource: (str(resource.name).casefold(), str(resource.id)),
    )
    wanted: str = reference.strip()
    for resource in active:
        if str(resource.id) == wanted:
            return resource

    matches: list[NameMatch[ResourceDocument]] = best_name_matches(
        wanted, [(resource, str(resource.name)) for resource in active]
    )
    if len(matches) == 1:
        return matches[0].item

    if matches:
        names: list[str] = [
            f"{match.item.name} (id {match.item.id})" for match in matches
        ]
        message: str = (
            f'"{wanted}" matches several: {"; ".join(names)}. Ask the customer '
            "which one they mean."
        )
        raise ValidationFailedError(
            message,
            reasons=[
                booking_refusal_reason(
                    BookingRefusalCode.AMBIGUOUS_RESOURCE, message, names
                )
            ],
        )

    available: list[str] = [
        f"{resource.name} (id {resource.id})"
        for resource in active[:MAX_LISTED_OPTIONS]
    ]
    message = f'Nobody and nothing bookable is called "{wanted}". Bookable: ' + (
        "; ".join(available) + "." if available else "none."
    )
    raise ValidationFailedError(
        message,
        reasons=[
            booking_refusal_reason(
                BookingRefusalCode.UNKNOWN_RESOURCE, message, [wanted]
            )
        ],
    )


def describe(offer: KnowledgeItemDocument) -> str:
    return f"{offer.title} (id {offer.id})"
