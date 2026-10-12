"""
What a brand's team may do in a business: pure rules, read on every
request from the brand and the business as stored now.

A brand member reaches a business only while the business names the
brand (`BusinessDocument.brand_id`): a location that left the brand, or
a brand member taken off its team, is out of reach at the next request.
A BRAND_OWNER acts as an owner of every location; a REGIONAL_MANAGER as
staff of the locations assigned to them, and nowhere else.
"""

from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.brands import BrandDocument, BrandMember
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId


def find_brand_member(brand: BrandDocument, user_id: UserId) -> BrandMember | None:
    """The person's place in the brand's team, or None."""

    for member in brand.members:
        if member.user_id == user_id:
            return member

    return None


def brand_grant(
    brand: BrandDocument,
    business: BusinessDocument,
    user_id: UserId,
) -> BusinessMemberRole | None:
    """The role the brand gives the person in the business, or None."""

    if business.brand_id != brand.id:
        return None

    member: BrandMember | None = find_brand_member(brand, user_id)
    if member is None:
        return None

    if member.role is BrandMemberRole.BRAND_OWNER:
        return BusinessMemberRole.OWNER

    if business.id in member.business_ids:
        return BusinessMemberRole.STAFF

    return None


def direct_role(
    business: BusinessDocument, user_id: UserId
) -> BusinessMemberRole | None:
    """The person's own role in the business's team, or None."""

    for member in business.members:
        if member.user_id == user_id:
            return member.role

    return None


def effective_role(
    direct: BusinessMemberRole | None,
    granted: BusinessMemberRole | None,
) -> BusinessMemberRole | None:
    """
    The role a person acts with: a brand owner is an owner even where the
    location's own team lists them otherwise; any other brand role never
    replaces the person's own role in the location.
    """

    if granted is BusinessMemberRole.OWNER:
        return granted

    return direct if direct is not None else granted


def visible_location_ids(
    brand: BrandDocument,
    user_id: UserId,
    location_ids: list[BusinessId],
) -> list[BusinessId]:
    """
    The brand's locations (`location_ids`, in their order) the person sees
    through the brand: all for a brand owner, the assigned ones for a
    regional manager, none for anyone else.
    """

    member: BrandMember | None = find_brand_member(brand, user_id)
    if member is None:
        return []

    if member.role is BrandMemberRole.BRAND_OWNER:
        return list(location_ids)

    assigned: set[BusinessId] = set(member.business_ids)
    return [location_id for location_id in location_ids if location_id in assigned]
