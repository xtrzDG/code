"""A paid subscription brings the assistant back to full service."""

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.schemas.constants.businesses import ServiceMode
from app.schemas.domain.businesses import BusinessDocument


def restore_full_service(
    business_repo: BusinessRepoContract,
    business: BusinessDocument,
    now: Microseconds,
) -> None:
    """
    Changed on the business as stored now, so an owner's edit saved while
    the payment was processed is kept; `business` gets the stored mode.
    """

    def switch_to_full_service(current: BusinessDocument) -> None:
        if current.service_mode is not ServiceMode.FULL:
            current.service_mode = ServiceMode.FULL
            current.updated_at = now

    business.service_mode = business_repo.update(
        business.id,
        switch_to_full_service,
    ).service_mode
