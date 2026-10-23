"""The closure's clock and the confirmation an owner types."""

from typed_time_provider import Microseconds

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.business_closures.constrained_integers import (
    OffboardAfterDays,
)
from app.schemas.typings.business_closures.constrained_strings import (
    BusinessNameConfirmation,
)

# A closed business is deleted this many days after it was closed (the
# export window of DPA 13.3), unless the closure is cancelled before.
CLOSURE_DAYS: int = 30
MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000


def deletion_moment(closed_at: Microseconds) -> Microseconds:
    """When a business closed at `closed_at` is deleted."""

    return Microseconds(int(closed_at) + CLOSURE_DAYS * MICROSECONDS_PER_DAY)


def offboarding_moment(
    unpaid_since: Microseconds, after_days: OffboardAfterDays
) -> Microseconds:
    """When a business whose service went unpaid at `unpaid_since` is closed."""

    return Microseconds(int(unpaid_since) + int(after_days) * MICROSECONDS_PER_DAY)


def require_name_confirmation(
    business: BusinessDocument, confirmation: BusinessNameConfirmation
) -> None:
    """
    The owner typed the business's name (case and outer spaces aside).

    Raises:
        ValidationFailedError: the typed name is not the business's.
    """

    if str(confirmation).strip().casefold() != str(business.name).strip().casefold():
        raise ValidationFailedError(
            "Type the business's name exactly to confirm closing it."
        )
