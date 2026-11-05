"""Loading the business a use case acts for, shared by every use-case package."""

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId


def require_business(
    business_repo: BusinessRepoContract,
    business_id: BusinessId,
) -> BusinessDocument:
    """The business of this id, or `NotFoundError` (404) when it is missing."""

    business: BusinessDocument | None = business_repo.get(business_id)
    if business is None:
        raise NotFoundError(f"Business {business_id} was not found.")

    return business
