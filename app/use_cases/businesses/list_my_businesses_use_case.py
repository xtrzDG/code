from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.businesses import BusinessView, BusinessViewSource
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.brand_reach import reachable_businesses


class ListMyBusinessesUseCase(UseCaseContract[UserId, list[BusinessView]]):
    """
    Return the businesses the user owns or works in, oldest first: their
    own teams' and the locations their brands give them (a brand owner's
    every location, a regional manager's assigned ones), each with the
    role the user acts with there.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        brand_repo: BrandRepoContract,
        user_repo: UserRepoContract,
        business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._brand_repo: BrandRepoContract = brand_repo
        self._user_repo: UserRepoContract = user_repo
        self._business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ] = business_view_transformer

    def run(self, input_data: UserId) -> list[BusinessView]:
        return [
            self._business_view_transformer.transform(
                BusinessViewSource(
                    business=item.business,
                    member_users=self._load_member_users(item.business),
                    viewer_id=input_data,
                    acting_role=item.role,
                )
            )
            for item in reachable_businesses(
                self._business_repo, self._brand_repo, input_data
            )
        ]

    def _load_member_users(self, business: BusinessDocument) -> list[UserDocument]:
        return [
            user
            for member in business.members
            if (user := self._user_repo.get(member.user_id)) is not None
        ]
