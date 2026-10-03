"""Pausing and resuming the assistant: the switches an owner may make."""

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.exceptions.application_errors import ConflictError

OWNER_STATUS_SWITCHES: frozenset[tuple[BusinessStatus, BusinessStatus]] = frozenset(
    {
        (BusinessStatus.LIVE, BusinessStatus.PAUSED),
        (BusinessStatus.PAUSED, BusinessStatus.LIVE),
    }
)


def check_status_switch(
    business: BusinessDocument,
    requested_status: BusinessStatus | None,
) -> BusinessStatus | None:
    """The status the owner switches to, or None when it stays."""

    if requested_status is None or requested_status is business.status:
        return None

    if (business.status, requested_status) not in OWNER_STATUS_SWITCHES:
        raise ConflictError(
            "Only a live assistant can be paused and only a paused one "
            f"resumed; the business is {business.status.value}."
        )

    return requested_status
