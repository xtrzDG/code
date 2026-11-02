"""
Who sees a conversation's platform details in the brain's cabinet tests:
the real `SeePlatformDetailsUseCase` over the world's users and an admin
team of the given people.
"""

from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.domain.users import UserDocument
from app.schemas.typings.users.booleans import IsPlatformAdmin
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.conversations.see_platform_details_use_case import (
    SeePlatformDetailsUseCase,
)
from tests.brain.brain_world import BrainWorld

type SeePlatformDetails = UseCaseContract[UserId, IsPlatformAdmin]


class AdminTeam(PlatformAdminRegistryContract):
    """An admin team of fixed people, all SUPER admins with passkeys."""

    def __init__(self, admins: frozenset[UserId]) -> None:
        self._admins: frozenset[UserId] = admins

    def role_of(self, user: UserDocument) -> PlatformAdminRole | None:
        return PlatformAdminRole.SUPER if user.id in self._admins else None

    def needs_passkey(self, user: UserDocument) -> bool:
        return False


def see_platform_details(
    world: BrainWorld, admins: frozenset[UserId]
) -> SeePlatformDetails:
    return SeePlatformDetailsUseCase(world.user_repo, AdminTeam(admins))
