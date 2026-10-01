from app.contracts.repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.businesses import BusinessQuery, BusinessView, BusinessViewSource


class GetBusinessUseCase(UseCaseContract[BusinessQuery, BusinessView]):
    """Return one business to its owners and staff (and audited admins)."""

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
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
            )
        )
