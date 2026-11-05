"""A platform admin team of fixed people, for tests of platform details."""

from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.domain.users import UserDocument
from app.schemas.typings.users.prefixed_id import UserId


class FixedAdminTeam(PlatformAdminRegistryContract):
    """The given people are SUPER admins (with passkeys); nobody else is."""

    def __init__(self, admins: frozenset[UserId] = frozenset()) -> None:
        self._admins: frozenset[UserId] = admins

    def role_of(self, user: UserDocument) -> PlatformAdminRole | None:
        return PlatformAdminRole.SUPER if user.id in self._admins else None

    def needs_passkey(self, user: UserDocument) -> bool:
        return False
