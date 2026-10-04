"""
The platform admin team: its stored records, and who is an admin with
which role right now.
"""

from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.contracts.repo_contract import RepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.typings.access.prefixed_id import PlatformAdminId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import EmailAddress

# The check every admin page and action starts with: the admin, when their
# role holds the permission (AuthorizePlatformAdminUseCase).
type PlatformAdminCheck = UseCaseContract[PlatformAdminAccessRequest, UserDocument]


class PlatformAdminRepoContract(RepoContract, Protocol):
    """The admin team (a platform collection; a handful of rows)."""

    def save(self, admin: PlatformAdminDocument) -> None:
        raise NotImplementedError

    def get(self, admin_id: PlatformAdminId) -> PlatformAdminDocument | None:
        raise NotImplementedError

    def delete(self, admin_id: PlatformAdminId) -> None:
        raise NotImplementedError

    def find_by_phone_number(
        self, phone_number: E164PhoneNumber
    ) -> PlatformAdminDocument | None:
        raise NotImplementedError

    def find_by_email(self, email: EmailAddress) -> PlatformAdminDocument | None:
        raise NotImplementedError

    def list_by_role(self, role: PlatformAdminRole) -> list[PlatformAdminDocument]:
        """The admins of one role (indexed)."""
        raise NotImplementedError

    def list_team(self) -> list[PlatformAdminDocument]:
        """The whole team, role by role, for the Team page."""
        raise NotImplementedError


class PlatformAdminRegistryContract(RegistryContract, Protocol):
    """Who is a platform admin, and with which role, at this moment."""

    def role_of(self, user: UserDocument) -> PlatformAdminRole | None:
        """
        The person's admin role, read from the admin team at every call
        (None: not an admin). While the team has no SUPER admin, a person
        on the PLATFORM_ADMIN_* lists is recorded as one (the bootstrap of
        a new platform); after that the lists grant nothing.
        """
        raise NotImplementedError
