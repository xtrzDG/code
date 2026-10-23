"""What keeps a person from deleting their account: businesses left without an owner."""

from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.users.prefixed_id import UserId


def is_sole_owner(business: BusinessDocument, user_id: UserId) -> bool:
    owners: list[UserId] = [
        member.user_id
        for member in business.members
        if member.role is BusinessMemberRole.OWNER
    ]
    return owners == [user_id]


def is_closing(
    closure_repo: BusinessClosureRepoContract, business: BusinessDocument
) -> bool:
    closure: BusinessClosureDocument | None = closure_repo.get(business.id)
    return closure is not None and closure.cancelled_at is None


def require_no_orphans(
    user_id: UserId,
    businesses: list[BusinessDocument],
    brands: list[BrandDocument],
    closure_repo: BusinessClosureRepoContract,
) -> None:
    """
    Refuse while the person is the last owner of a business that is not
    closing (close it, or make someone else an owner, first) or the last
    owner of a brand: nobody could run them after the account is gone.

    Raises:
        ConflictError: naming those businesses and brands.
    """

    orphans: list[str] = [
        str(business.name)
        for business in businesses
        if is_sole_owner(business, user_id) and not is_closing(closure_repo, business)
    ]
    orphans += [
        str(brand.name)
        for brand in brands
        if [
            member.user_id
            for member in brand.members
            if member.role is BrandMemberRole.BRAND_OWNER
        ]
        == [user_id]
    ]
    if orphans:
        raise ConflictError(
            "You are the last owner of "
            + ", ".join(orphans)
            + ": close the business in Settings → Business, or make another "
            "person an owner, before deleting your account."
        )
