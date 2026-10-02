from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.businesses import BusinessView, BusinessViewSource
from app.schemas.typings.users.prefixed_id import UserId


class ListMyBusinessesUseCase(UseCaseContract[UserId, list[BusinessView]]):
    """Return the businesses the user owns or works in, oldest first."""

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._user_repo: UserRepoContract = user_repo
        self._business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ] = business_view_transformer

    def run(self, input_data: UserId) -> list[BusinessView]:
        businesses: list[BusinessDocument] = sorted(
            self._business_repo.list_by_member(input_data),
            key=lambda business: business.created_at,
        )
        return [
            self._business_view_transformer.transform(
                BusinessViewSource(
                    business=business,
                    member_users=self._load_member_users(business),
                    viewer_id=input_data,
                )
            )
            for business in businesses
        ]

    def _load_member_users(self, business: BusinessDocument) -> list[UserDocument]:
        return [
            user
            for member in business.members
            if (user := self._user_repo.get(member.user_id)) is not None
        ]
