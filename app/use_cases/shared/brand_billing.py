"""
Billing a brand (R17): one setup fee for the whole brand, and each further
location at the plan's additional-location price. Both are read as stored
now, so a location that joins or leaves a brand is priced by where it is
when its subscription is priced or its first period invoiced.
"""

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.brands.booleans import (
    IsAdditionalLocation,
    IsBrandSetupFeeCovered,
)
from app.utilities.brands.brand_locations import is_further_location


def is_additional_location(
    business_repo: BusinessRepoContract, business: BusinessDocument
) -> IsAdditionalLocation:
    """Whether the business is a further location of its brand."""

    if business.brand_id is None:
        return False

    return is_further_location(business, business_repo.list_by_brand(business.brand_id))


def is_setup_fee_covered(
    brand_repo: BrandRepoContract,
    business_repo: BusinessRepoContract,
    business: BusinessDocument,
) -> IsBrandSetupFeeCovered:
    """
    Whether another location carries the brand's one setup fee, as read
    now and without claiming it: true for a further location, and for a
    first location once the fee was claimed by another one (the first
    location left the brand after paying it). A quote, never a charge;
    invoicing claims the fee (`owes_brand_setup_fee`).
    """

    if business.brand_id is None:
        return False

    if is_additional_location(business_repo, business):
        return True

    brand: BrandDocument | None = brand_repo.get(business.brand_id)
    return (
        brand is not None
        and brand.setup_fee_business_id is not None
        and brand.setup_fee_business_id != business.id
    )


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
