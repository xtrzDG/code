"""Choosing the resources a booking may use, and their booking rules.

Resources are tried best fit first (smallest capacity that seats the party,
then name), so a table for two is not given to a couple when a table for
eight is also free.
"""

from collections.abc import Sequence

from app.schemas.constants.bookings import (
    BookingRefusalCode,
    ResourceKind,
)
from app.schemas.domain.profiles import BookingRules
from app.schemas.domain.resources import ResourceDocument
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.utilities.scheduling.availability import DEFAULT_SLOT_MINUTES
from app.utilities.scheduling.placement_errors import booking_refusal_reason
from app.utilities.scheduling.zoned_time import SECONDS_PER_MINUTE


def select_resources(
    resources: Sequence[ResourceDocument],
    resource_id: ResourceId | None,
    resource_kind: ResourceKind | None,
    rules: BookingRules | None,
) -> list[ResourceDocument]:
    """
    Active resources matching the request: one resource by id (NotFoundError
    when missing or inactive), else a kind (requested, else the profile's),
    else every active resource. A profile kind without resources falls back
    to every active resource.
    """

    active: list[ResourceDocument] = [
        resource for resource in resources if resource.is_active
    ]
    if resource_id is not None:
        matching: list[ResourceDocument] = [
            resource for resource in active if resource.id == resource_id
        ]
        if not matching:
            raise NotFoundError(f"Resource {resource_id} was not found.")

        return matching

    if resource_kind is not None:
        return [resource for resource in active if resource.kind is resource_kind]

    if rules is not None:
        of_profile_kind: list[ResourceDocument] = [
            resource for resource in active if resource.kind is rules.resource_kind
        ]
        if of_profile_kind:
            return of_profile_kind

    return active


def seating_resources(
    resources: Sequence[ResourceDocument],
    party_size: PartySize | None,
) -> list[ResourceDocument]:
    """Resources that seat the party, best fit first."""

    fitting: list[ResourceDocument] = [
        resource
        for resource in resources
        if party_size is None or int(resource.capacity) >= int(party_size)
    ]
    return sorted(fitting, key=lambda resource: (int(resource.capacity), resource.name))


def ensure_party_size_allowed(
    party_size: PartySize, rules: BookingRules | None
) -> None:
    """Online bookings are limited to the profile's maximum party size."""

    if rules is not None and int(party_size) > int(rules.max_party_size):
        message: str = (
            f"Online booking is limited to {int(rules.max_party_size)} guests; "
            f"a party of {int(party_size)} is handled by a manager (create a lead "
            "or hand off)."
        )
        raise ValidationFailedError(
            message,
            reasons=[
                booking_refusal_reason(
                    BookingRefusalCode.PARTY_TOO_LARGE,
                    message,
                    [str(int(rules.max_party_size))],
                )
            ],
        )


def min_notice_seconds(rules: BookingRules | None) -> int:
    if rules is None:
        return 0

    return int(rules.min_notice_minutes) * SECONDS_PER_MINUTE


def resolve_duration_minutes(
    requested: BookingDurationMinutes | None,
    resource: ResourceDocument,
    rules: BookingRules | None,
) -> int:
    """Requested length, else the resource's slot, else the profile's slot."""

    if requested is not None:
        return int(requested)

    if resource.slot_minutes is not None:
        return int(resource.slot_minutes)

    if rules is not None:
        return int(rules.slot_minutes)

    return DEFAULT_SLOT_MINUTES
