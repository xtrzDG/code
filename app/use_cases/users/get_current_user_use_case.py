from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.users import CurrentUserView, UserMembershipView, UserView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.platform_admins import is_listed_platform_admin


class GetCurrentUserUseCase(UseCaseContract[UserId, CurrentUserView]):
    """
    Return the signed-in user and their businesses, oldest business first,
    and how the current session is signed in. `is_platform_admin` follows
    the PLATFORM_ADMIN_* lists of now, so the cabinet stops offering the
    admin pages to someone taken off them.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        business_repo: BusinessRepoContract,
        user_view_transformer: TransformerContract[UserDocument, UserView],
        session_assurance: SessionAssuranceContract,
        app_settings: AppSettings,
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._user_view_transformer: TransformerContract[UserDocument, UserView] = (
            user_view_transformer
        )
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: UserId) -> CurrentUserView:
        stored: UserDocument | None = self._user_repo.get(input_data)
        if stored is None:
            raise NotFoundError(f"User {input_data} was not found.")

        user: UserDocument = stored.model_copy(
            update={
                "is_platform_admin": is_listed_platform_admin(
                    stored, self._app_settings
                )
            }
        )
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
        assurance: SessionAssurance | None = self._session_assurance.current()
        return CurrentUserView(
            user=self._user_view_transformer.transform(user),
            memberships=memberships,
            auth_level=assurance.auth_level
            if assurance is not None and assurance.user_id == user.id
            else None,
        )
