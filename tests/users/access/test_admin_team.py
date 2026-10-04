"""
The platform admin team: SUPER admins add people by phone or e-mail with
a role, change roles and take people off; the team never loses its last
SUPER; other roles cannot manage it; every change is audited.
"""

import pytest

from app.schemas.constants.access import PlatformAdminRole
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import (
    AddPlatformAdminCommand,
    ChangePlatformAdminRoleCommand,
    PlatformAdminTeamQuery,
    PlatformAdminTeamView,
    RemovePlatformAdminCommand,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.strings import RawEmailAddressInput
from app.use_cases.admin.authorize_platform_admin_use_case import (
    AuthorizePlatformAdminUseCase,
)
from app.use_cases.admin.team.add_platform_admin_use_case import (
    AddPlatformAdminUseCase,
)
from app.use_cases.admin.team.change_platform_admin_role_use_case import (
    ChangePlatformAdminRoleUseCase,
)
from app.use_cases.admin.team.list_platform_admins_use_case import (
    ListPlatformAdminsUseCase,
)
from app.use_cases.admin.team.remove_platform_admin_use_case import (
    RemovePlatformAdminUseCase,
)
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from tests.foundation.access_support import AllowStepUp
from tests.users.access.support_world import SUPPORT_IP, SupportWorld


class TeamWorld(SupportWorld):
    """The support world's SUPER admin manages the platform admin team."""

    def __init__(self, role: PlatformAdminRole = PlatformAdminRole.SUPER) -> None:
        super().__init__(role)
        testbed = self.testbed
        wall_clock = testbed.clock.build_wall_clock()
        authorize = AuthorizePlatformAdminUseCase(
            testbed.user_repo, testbed.session_assurance, testbed.platform_admins
        )
        repo = testbed.platform_admin_repo
        self.list_team = ListPlatformAdminsUseCase(authorize, repo, testbed.user_repo)
        self.add = AddPlatformAdminUseCase(
            authorize,
            repo,
            testbed.user_repo,
            PhoneNumberParser(),
            testbed.audit_log_repo,
            wall_clock,
            AllowStepUp(),
        )
        self.change = ChangePlatformAdminRoleUseCase(
            authorize,
            repo,
            testbed.user_repo,
            testbed.audit_log_repo,
            wall_clock,
            AllowStepUp(),
        )
        self.remove = RemovePlatformAdminUseCase(
            authorize, repo, testbed.audit_log_repo, wall_clock, AllowStepUp()
        )

    def add_by(
        self,
        role: PlatformAdminRole,
        phone: str | None = None,
        email: str | None = None,
    ) -> PlatformAdminTeamView:
        return self.as_support(
            lambda: self.add.run(
                AddPlatformAdminCommand(
                    user_id=self.support.id,
                    phone_number=None if phone is None else RawPhoneNumberInput(phone),
                    email=None if email is None else RawEmailAddressInput(email),
                    role=role,
                    client_ip_address=ClientIpAddress(SUPPORT_IP),
                )
            )
        )

    def team(self, viewer: UserDocument | None = None) -> PlatformAdminTeamView:
        user = viewer or self.support
        return self.as_support(
            lambda: self.list_team.run(PlatformAdminTeamQuery(user_id=user.id))
        )


def team_changes(world: TeamWorld) -> list[str]:
    return sorted(
        str(entry.entity_id).split(":")[-1]
        for entry in world.testbed.audit_log_collection.list_all()
        if entry.action is AuditAction.PLATFORM_ADMIN_CHANGED
    )


def test_a_super_admin_adds_people_by_phone_or_email() -> None:
    world = TeamWorld()

    world.add_by(PlatformAdminRole.SUPPORT_READONLY, phone="+995 555 12 34 56")
    team = world.add_by(PlatformAdminRole.BILLING, email=" Billing@Platform.example ")

    roles = [(item.role, item.login_method) for item in team.items]
    assert roles == [
        (PlatformAdminRole.SUPER, LoginMethod.EMAIL),
        (PlatformAdminRole.SUPPORT_READONLY, LoginMethod.PHONE),
        (PlatformAdminRole.BILLING, LoginMethod.EMAIL),
    ]
    [me] = [item for item in team.items if item.is_you]
    assert me.user_id == world.support.id
    assert str(team.items[1].phone_number) == "+995555123456"
    assert str(team.items[2].email) == "billing@platform.example"
    assert team.items[2].user_id is None
    assert (team.items[0].added_by, team.items[2].added_by) == (None, world.support.id)
    assert team_changes(world) == ["billing", "support_readonly"]


def test_one_person_is_added_once_with_one_destination() -> None:
    world = TeamWorld()
    world.add_by(PlatformAdminRole.BILLING, email="billing@platform.example")

    with pytest.raises(ConflictError):
        world.add_by(PlatformAdminRole.SUPER, email="BILLING@platform.example")
    with pytest.raises(ValidationFailedError):
        world.add_by(
            PlatformAdminRole.BILLING,
            phone="+995555123456",
            email="both@platform.example",
        )
    with pytest.raises(ValidationFailedError):
        world.add_by(PlatformAdminRole.BILLING)


def test_roles_change_and_people_leave_but_one_super_always_stays() -> None:
    world = TeamWorld()
    team = world.add_by(
        PlatformAdminRole.SUPPORT_READONLY, email="ops@platform.example"
    )
    me, other = team.items

    with pytest.raises(ConflictError, match="at least one SUPER"):
        world.as_support(
            lambda: world.change.run(
                ChangePlatformAdminRoleCommand(
                    user_id=world.support.id,
                    admin_id=me.id,
                    role=PlatformAdminRole.BILLING,
                )
            )
        )
    with pytest.raises(ConflictError, match="at least one SUPER"):
        world.as_support(
            lambda: world.remove.run(
                RemovePlatformAdminCommand(user_id=world.support.id, admin_id=me.id)
            )
        )
    promoted = world.as_support(
        lambda: world.change.run(
            ChangePlatformAdminRoleCommand(
                user_id=world.support.id,
                admin_id=other.id,
                role=PlatformAdminRole.SUPER,
            )
        )
    )
    assert [item.role for item in promoted.items] == [PlatformAdminRole.SUPER] * 2
    world.as_support(
        lambda: world.remove.run(
            RemovePlatformAdminCommand(user_id=world.support.id, admin_id=me.id)
        )
    )

    assert world.testbed.platform_admin_repo.get(me.id) is None
    assert world.testbed.platform_admins.role_of(world.support) is None
    assert team_changes(world) == ["removed", "super", "support_readonly"]


@pytest.mark.parametrize(
    "role", [PlatformAdminRole.SUPPORT_READONLY, PlatformAdminRole.BILLING]
)
def test_other_roles_cannot_manage_the_team(role: PlatformAdminRole) -> None:
    world = TeamWorld(role)

    with pytest.raises(AccessDeniedError, match="role does not include"):
        world.team()
    with pytest.raises(AccessDeniedError, match="role does not include"):
        world.add_by(PlatformAdminRole.SUPER, email="me-again@platform.example")


def test_people_outside_the_team_are_refused() -> None:
    world = TeamWorld()
    owner = world.testbed.user_repo.get(world.owner_id)
    assert owner is not None

    with pytest.raises(AccessDeniedError, match="Only platform admins"):
        world.team(owner)
