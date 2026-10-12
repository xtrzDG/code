"""
Which businesses a person reaches, and with which role, counting the
brands they belong to; shared by the access check, the current user and
the business list. Everything is read as stored now, so a member taken
off a brand (or a location taken out of it) is out at the next request.
"""

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.brands import BrandDocument, BrandMember
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.brands.brand_reach import BusinessReach
from app.schemas.typings.brands.prefixed_id import BrandId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.brands.brand_access import (
    brand_grant,
    direct_role,
    effective_role,
    find_brand_member,
)


def brand_role_in(
    brand_repo: BrandRepoContract,
    business: BusinessDocument,
    user_id: UserId,
) -> BusinessMemberRole | None:
    """The role the business's brand gives the person there, or None."""

    if business.brand_id is None:
        return None

    brand: BrandDocument | None = brand_repo.get(business.brand_id)
    if brand is None:
        return None

    return brand_grant(brand, business, user_id)


def acting_role(
    brand_repo: BrandRepoContract,
    business: BusinessDocument,
    user_id: UserId,
) -> BusinessMemberRole | None:
    """The role the person acts with in the business (own or brand's)."""

    return effective_role(
        direct_role(business, user_id), brand_role_in(brand_repo, business, user_id)
    )


def brand_locations_of(
    business_repo: BusinessRepoContract,
    brand: BrandDocument,
    member: BrandMember,
) -> list[BusinessDocument]:
    """The brand's locations the member reaches through it, oldest first."""

    if member.role is BrandMemberRole.BRAND_OWNER:
        return business_repo.list_by_brand(brand.id)

    assigned: list[BusinessDocument] = business_repo.get_many(list(member.business_ids))
    return sorted(
        (business for business in assigned if business.brand_id == brand.id),
        key=lambda business: business.created_at,
    )


def reachable_businesses(
    business_repo: BusinessRepoContract,
    brand_repo: BrandRepoContract,
    user_id: UserId,
) -> list[BusinessReach]:
    """Every business the person works in, oldest first, with their role."""

    found: dict[BusinessId, BusinessDocument] = {
        business.id: business for business in business_repo.list_by_member(user_id)
    }
    brands: dict[BrandId, BrandDocument] = {}
    for brand in brand_repo.list_by_member(user_id):
        member: BrandMember | None = find_brand_member(brand, user_id)
        if member is None:
            continue

        brands[brand.id] = brand
        for location in brand_locations_of(business_repo, brand, member):
            found.setdefault(location.id, location)

    reach: list[BusinessReach] = []
    for business in sorted(found.values(), key=lambda item: item.created_at):
        brand: BrandDocument | None = (
            None if business.brand_id is None else brands.get(business.brand_id)
        )
        role: BusinessMemberRole | None = effective_role(
            direct_role(business, user_id),
            None if brand is None else brand_grant(brand, business, user_id),
        )
        if role is not None:
            reach.append(BusinessReach(business=business, role=role, brand=brand))

    return reach
