from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.businesses import BusinessQuery, BusinessView, BusinessViewSource
from app.use_cases.shared.brand_reach import acting_role


class GetBusinessUseCase(UseCaseContract[BusinessQuery, BusinessView]):
    """
    Return one business to its owners and staff, its brand's team (and
    audited admins), with the role the viewer acts with there.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        brand_repo: BrandRepoContract,
        user_repo: UserRepoContract,
        business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._brand_repo: BrandRepoContract = brand_repo
        self._user_repo: UserRepoContract = user_repo
        self._business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ] = business_view_transformer

    def run(self, input_data: BusinessQuery) -> BusinessView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        member_users: list[UserDocument] = [
            user
            for member in business.members
            if (user := self._user_repo.get(member.user_id)) is not None
        ]
        return self._business_view_transformer.transform(
            BusinessViewSource(
                business=business,
                member_users=member_users,
                viewer_id=input_data.user_id,
                acting_role=acting_role(self._brand_repo, business, input_data.user_id),
            )
        )
