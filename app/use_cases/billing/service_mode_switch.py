"""Switch how the assistant serves a business, without losing an owner's edit."""

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.schemas.constants.businesses import ServiceMode
from app.schemas.domain.businesses import BusinessDocument


def switch_service_mode(
    business_repo: BusinessRepoContract,
    business: BusinessDocument,
    service_mode: ServiceMode,
    now: Microseconds,
) -> bool:
    """
    Switch the mode of the business as stored now (one atomic change, so
    an owner's edit saved meanwhile is kept); return False when it
    already was that mode.
    """

    switched: list[bool] = []

    def switch_mode(current: BusinessDocument) -> None:
        if current.service_mode is not service_mode:
            current.service_mode = service_mode
            current.updated_at = now
            switched.append(True)

    business_repo.update(business.id, switch_mode)
    business.service_mode = service_mode
    return bool(switched)
