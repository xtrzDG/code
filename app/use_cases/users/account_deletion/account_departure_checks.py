"""What keeps a person from deleting their account: businesses left without an owner."""

from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.users.prefixed_id import UserId

# The refusal's reason codes; their details are the ids the cabinet names.
LAST_BUSINESS_OWNER: ErrorReasonCode = ErrorReasonCode("last_business_owner")
LAST_BRAND_OWNER: ErrorReasonCode = ErrorReasonCode("last_brand_owner")


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

    businesses_left: list[BusinessDocument] = [
        business
        for business in businesses
        if is_sole_owner(business, user_id) and not is_closing(closure_repo, business)
    ]
    brands_left: list[BrandDocument] = [
        brand
        for brand in brands
        if [
            member.user_id
            for member in brand.members
            if member.role is BrandMemberRole.BRAND_OWNER
        ]
        == [user_id]
    ]
    if not businesses_left and not brands_left:
        return

    names: list[str] = [str(business.name) for business in businesses_left] + [
        str(brand.name) for brand in brands_left
    ]
    message: str = (
        "You are the last owner of "
        + ", ".join(names)
        + ": close the business in Settings → Business, or make another "
        "person an owner, before deleting your account."
    )
    reasons: list[ErrorReason] = []
    if businesses_left:
        reasons.append(
            ErrorReason(
                code=LAST_BUSINESS_OWNER,
                message=ErrorReasonMessage(message),
                details=[
                    ErrorReasonDetail(str(business.id)) for business in businesses_left
                ],
            )
        )
    if brands_left:
        reasons.append(
            ErrorReason(
                code=LAST_BRAND_OWNER,
                message=ErrorReasonMessage(message),
                details=[ErrorReasonDetail(str(brand.id)) for brand in brands_left],
            )
        )
    raise ConflictError(message, reasons=reasons)
