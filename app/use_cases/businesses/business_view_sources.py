"""What a business view is shaped from, for the viewer who asked."""

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.businesses import BusinessViewSource
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.brand_reach import acting_role


def business_view_source(
    business: BusinessDocument,
    viewer_id: UserId,
    user_repo: UserRepoContract,
    brand_repo: BrandRepoContract,
) -> BusinessViewSource:
    """
    The business with the users behind its members and the role the
    viewer acts with there (`acting_role`: their own, or the one their
    brand gives them), so a change answers with the same view as a read.
    """

    member_users: list[UserDocument] = [
        user
        for member in business.members
        if (user := user_repo.get(member.user_id)) is not None
    ]
    return BusinessViewSource(
        business=business,
        member_users=member_users,
        viewer_id=viewer_id,
        acting_role=acting_role(brand_repo, business, viewer_id),
    )
