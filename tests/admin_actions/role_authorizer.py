"""The admin check by role (the production permission table), for tests."""

from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.admin_permissions import has_permission


class RoleAuthorizer(UseCaseContract[PlatformAdminAccessRequest, UserDocument]):
    """
    Each person's admin role as the test set it; the permission a page or
    action needs comes from `admin_permissions` as in production (the
    two-factor part of the real check is tested in tests/users/access).
    """

    def __init__(self, user_repo: UserRepoContract) -> None:
        self._user_repo: UserRepoContract = user_repo
        self.roles: dict[UserId, PlatformAdminRole] = {}

    def run(self, input_data: PlatformAdminAccessRequest) -> UserDocument:
        user = self._user_repo.get(input_data.user_id)
        role = self.roles.get(input_data.user_id)
        if user is None or not has_permission(role, input_data.permission):
            raise AccessDeniedError("Your platform admin role does not include this.")

        return user
