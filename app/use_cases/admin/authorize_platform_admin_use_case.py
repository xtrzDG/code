from app.contracts.repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.users import UserDocument
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.users.prefixed_id import UserId


class AuthorizePlatformAdminUseCase(UseCaseContract[UserId, UserDocument]):
    """
    Return the user when they are a platform admin (concept /admin).

    Only `UserDocument.is_platform_admin` counts; owning or working for a
    business never grants admin pages.
    """

    def __init__(self, user_repo: UserRepoContract) -> None:
        self._user_repo: UserRepoContract = user_repo

    def run(self, input_data: UserId) -> UserDocument:
        user: UserDocument | None = self._user_repo.get(input_data)
        if user is None or not user.is_platform_admin:
            raise AccessDeniedError("Only platform admins may open the admin pages.")

        return user
