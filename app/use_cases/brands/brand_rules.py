"""Checks several brand use cases share: names, location ownership, the team."""

from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.brands.strings import BrandName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.brands.brand_access import direct_role

MAX_BRAND_NAME_LENGTH: int = 100


def require_valid_brand_name(name: BrandName) -> None:
    """
    Raises:
        ValidationFailedError: blank, or longer than MAX_BRAND_NAME_LENGTH.
    """

    if name.strip() == "" or len(name) > MAX_BRAND_NAME_LENGTH:
        raise ValidationFailedError(
            f"A brand name has 1 to {MAX_BRAND_NAME_LENGTH} characters."
        )


def require_own_business(
    business: BusinessDocument | None,
    business_id: BusinessId,
    user_id: UserId,
) -> BusinessDocument:
    """
    The business, when the person is one of its own owners: only they may
    bring it into a brand (a brand owner owns its locations through the
    brand, which is no consent to join another one).

    Raises:
        NotFoundError: no such business, or the person is not on its team.
        AccessDeniedError: the person is on its team but not an owner.
    """

    role: BusinessMemberRole | None = (
        None if business is None else direct_role(business, user_id)
    )
    if business is None or role is None:
        raise NotFoundError(f"Business {business_id} was not found.")

    if role is not BusinessMemberRole.OWNER:
        raise AccessDeniedError("Only an owner of the business may add it to a brand.")

    return business


def require_free_of_brands(business: BusinessDocument) -> None:
    """
    Raises:
        ConflictError: the business is already a location of a brand.
    """

    if business.brand_id is not None:
        raise ConflictError(
            "This business is already a location of a brand: take it out first."
        )


def count_brand_owners(brand: BrandDocument) -> int:
    return sum(
        1 for member in brand.members if member.role is BrandMemberRole.BRAND_OWNER
    )


def require_another_owner_stays(brand: BrandDocument, leaving: UserId) -> None:
    """
    Raises:
        ConflictError: `leaving` is the brand's last owner.
    """

    is_owner: bool = any(
        member.user_id == leaving and member.role is BrandMemberRole.BRAND_OWNER
        for member in brand.members
    )
    if is_owner and count_brand_owners(brand) <= 1:
        raise ConflictError("A brand keeps at least one owner.")


def assigned_locations(
    role: BrandMemberRole,
    business_ids: list[BusinessId],
    location_ids: list[BusinessId],
) -> list[BusinessId]:
    """
    The locations a member of this role is assigned: none for a brand
    owner (they reach every one), at least one of the brand's own for a
    regional manager.

    Raises:
        ValidationFailedError: a manager without locations, or with a
            business that is no location of the brand.
    """

    if role is BrandMemberRole.BRAND_OWNER:
        return []

    if not business_ids:
        raise ValidationFailedError("Choose the locations this manager runs.")

    known: set[BusinessId] = set(location_ids)
    if any(business_id not in known for business_id in business_ids):
        raise ValidationFailedError("A manager runs locations of this brand only.")

    return list(dict.fromkeys(business_ids))


def reached_locations(
    role: BrandMemberRole,
    assigned: list[BusinessId],
    location_ids: list[BusinessId],
) -> list[BusinessId]:
    """The locations a member of this role reaches through the brand."""

    return list(location_ids) if role is BrandMemberRole.BRAND_OWNER else assigned
