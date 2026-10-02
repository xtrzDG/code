from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.users import CurrentUserView, UserMembershipView, UserView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.users.prefixed_id import UserId


class GetCurrentUserUseCase(UseCaseContract[UserId, CurrentUserView]):
    """Return the signed-in user and their businesses, oldest business first."""

    def __init__(
        self,
        user_repo: UserRepoContract,
        business_repo: BusinessRepoContract,
        user_view_transformer: TransformerContract[UserDocument, UserView],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._user_view_transformer: TransformerContract[UserDocument, UserView] = (
            user_view_transformer
        )

    def run(self, input_data: UserId) -> CurrentUserView:
        user: UserDocument | None = self._user_repo.get(input_data)
        if user is None:
            raise NotFoundError(f"User {input_data} was not found.")

        businesses: list[BusinessDocument] = sorted(
            self._business_repo.list_by_member(user.id),
            key=lambda business: business.created_at,
        )
        memberships: list[UserMembershipView] = [
            UserMembershipView(
                business_id=business.id,
                business_name=business.name,
                role=member.role,
                business_status=business.status,
                country_code=business.country_code,
            )
            for business in businesses
            for member in business.members
            if member.user_id == user.id
        ]
        return CurrentUserView(
            user=self._user_view_transformer.transform(user),
            memberships=memberships,
        )
