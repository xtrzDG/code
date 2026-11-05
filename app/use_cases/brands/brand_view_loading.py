"""Building the brand a use case answers with, shared by the brand use cases."""

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.domain.brands import BrandDocument, BrandMember
from app.schemas.domain.users import UserDocument
from app.schemas.dto.brands.brand_views import BrandView, BrandViewSource
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.brands.brand_access import find_brand_member


class BrandViewLoader:
    """
    The brand as one member sees it: its locations (read by the brand id,
    the one source of truth) and, for a brand owner, the users of its team.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        brand_view_transformer: TransformerContract[BrandViewSource, BrandView],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._user_repo: UserRepoContract = user_repo
        self._transformer: TransformerContract[BrandViewSource, BrandView] = (
            brand_view_transformer
        )

    def load(self, brand: BrandDocument, viewer_id: UserId) -> BrandView:
        viewer: BrandMember | None = find_brand_member(brand, viewer_id)
        member_users: list[UserDocument] = (
            [
                user
                for member in brand.members
                if (user := self._user_repo.get(member.user_id)) is not None
            ]
            if viewer is not None and viewer.role is BrandMemberRole.BRAND_OWNER
            else []
        )
        return self._transformer.transform(
            BrandViewSource(
                brand=brand,
                locations=self._business_repo.list_by_brand(brand.id),
                member_users=member_users,
                viewer_id=viewer_id,
            )
        )
