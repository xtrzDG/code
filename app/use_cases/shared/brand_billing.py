"""
Billing a brand (R17): one setup fee for the whole brand, and each further
location at the plan's additional-location price. Both are read as stored
now, so a location that joins or leaves a brand is priced by where it is
when its subscription is priced or its first period invoiced.
"""

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.brands.booleans import IsAdditionalLocation
from app.utilities.brands.brand_locations import is_further_location


def is_additional_location(
    business_repo: BusinessRepoContract, business: BusinessDocument
) -> IsAdditionalLocation:
    """Whether the business is a further location of its brand."""

    if business.brand_id is None:
        return False

    return is_further_location(business, business_repo.list_by_brand(business.brand_id))


def owes_brand_setup_fee(
    brand_repo: BrandRepoContract,
    business_repo: BusinessRepoContract,
    business: BusinessDocument,
) -> bool:
    """
    Whether this business carries its brand's one setup fee, asked only
    once everything else says the fee is due. A business outside any brand
    carries its own. In a brand only the first location does, and only by
    claiming the fee on the brand in one atomic step: a further location
    never pays one, and a location that becomes first after the fee was
    claimed (the first one left) does not pay it again.
    """

    if business.brand_id is None:
        return True

    if is_additional_location(business_repo, business):
        return False

    return brand_repo.claim_setup_fee(business.brand_id, business.id)
