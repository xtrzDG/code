from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.users import UserDocument
from app.schemas.typings.users.booleans import IsPlatformAdmin
from app.schemas.typings.users.prefixed_id import UserId


class SeePlatformDetailsUseCase(UseCaseContract[UserId, IsPlatformAdmin]):
    """
    Whether this person sees a conversation's platform details (tool call
    inputs and results, the model, tokens and cost;
    `app/utilities/conversations/platform_details.py`): only a platform
    admin of now, read from the admin team at every call, so someone taken
    off it stops seeing them with the next request. The stored
    `is_platform_admin` flag is never trusted for this.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        platform_admins: PlatformAdminRegistryContract,
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._platform_admins: PlatformAdminRegistryContract = platform_admins

    def run(self, input_data: UserId) -> IsPlatformAdmin:
        user: UserDocument | None = self._user_repo.get(input_data)
        return user is not None and self._platform_admins.role_of(user) is not None
