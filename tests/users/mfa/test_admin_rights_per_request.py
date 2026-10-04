"""
Admin rights are read from the admin team at every check: someone taken
off the team, or given a role without the permission, is refused at the
next request although the stored flag (refreshed only at sign-in) still
says admin; the PLATFORM_ADMIN_* lists only bootstrap the first SUPER
admin; a session without two factors never opens admin access.
"""

from collections.abc import Callable
from contextvars import copy_context
from functools import partial

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.business_repositories import BusinessRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.access import PlatformAdminPermission, PlatformAdminRole
from app.schemas.constants.mfa import AuthLevel
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import AccessDeniedError, NotFoundError
from app.schemas.exceptions.mfa_errors import MfaRequiredError
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.authorize_platform_admin_use_case import (
    AuthorizePlatformAdminUseCase,
)
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.utilities.security.platform_admin_ids import derive_platform_admin_id
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.foundation.access_support import (
    PLATFORM_ADMIN_EMAIL,
    platform_admin,
    settings_with_admins,
    signed_in,
)
from tests.foundation.builders import build_business
from tests.foundation.support_access_builders import (
    build_authorize_business_access,
    in_memory_grant_repo,
    in_memory_platform_admin_repo,
    in_memory_platform_admins,
    open_support_session,
)
from tests.storage.storage_testing import build_fixed_wall_clock

SECOND_LISTED_EMAIL: str = "second-admin@example.com"
NOW: int = int(build_fixed_wall_clock().now_unix())


class World:
    def __init__(self) -> None:
        self.users = UserRepository(InMemoryDocumentCollectionAdapter(UserDocument))
        self.businesses = BusinessRepository(
            InMemoryDocumentCollectionAdapter(BusinessDocument)
        )
        self.audit_entries = InMemoryDocumentCollectionAdapter(AuditLogEntryDocument)
        self.sessions = SessionAssuranceContext()
        self.team = in_memory_platform_admin_repo()
        self.grants = in_memory_grant_repo()
        self.wall_clock = build_fixed_wall_clock()
        self.admins = in_memory_platform_admins(
            self.wall_clock,
            settings_with_admins([PLATFORM_ADMIN_EMAIL, SECOND_LISTED_EMAIL]),
            self.team,
        )
        self.admin: UserDocument = platform_admin()
        self.users.save(self.admin)
        self.business: BusinessDocument = build_business(UserId())
        self.businesses.save(self.business)

    def platform_check(self) -> AuthorizePlatformAdminUseCase:
        return AuthorizePlatformAdminUseCase(self.users, self.sessions, self.admins)

    def business_check(self) -> AuthorizeBusinessAccessUseCase:
        return build_authorize_business_access(
            business_repo=self.businesses,
            user_repo=self.users,
            audit_log_repo=AuditLogRepository(self.audit_entries),
            wall_clock=self.wall_clock,
            session_assurance=self.sessions,
            grant_repo=self.grants,
            platform_admins=self.admins,
        )

    def in_request[T](self, assurance: SessionAssurance, work: Callable[[], T]) -> T:
        """Run `work` as a request of this session (its own context)."""

        def request() -> T:
            self.sessions.bind(assurance)
            return work()

        return copy_context().run(request)


def add_admin(world: World, email: str, role: PlatformAdminRole) -> None:
    address = EmailAddress(email)
    world.team.save(
        PlatformAdminDocument(
            id=derive_platform_admin_id(LoginMethod.EMAIL, address),
            login_method=LoginMethod.EMAIL,
            email=address,
            role=role,
        )
    )


def needs(
    user_id: UserId,
    permission: PlatformAdminPermission = PlatformAdminPermission.VIEW_CLIENTS,
) -> PlatformAdminAccessRequest:
    return PlatformAdminAccessRequest(user_id=user_id, permission=permission)


def test_the_lists_bootstrap_only_the_first_super_admin() -> None:
    world = World()
    second = UserDocument(
        login_method=world.admin.login_method,
        email=EmailAddress(SECOND_LISTED_EMAIL),
        locale=world.admin.locale,
        is_verified=True,
    )
    world.users.save(second)

    assert world.admins.role_of(world.admin) is PlatformAdminRole.SUPER
    assert [admin.email for admin in world.team.list_team()] == [world.admin.email]
    # Listed too, but a SUPER admin exists: the Team page adds people now.
    assert world.admins.role_of(second) is None


def test_an_admin_taken_off_the_team_is_refused_at_the_next_request() -> None:
    world = World()
    session = signed_in(world.admin.id)
    allowed = world.in_request(
        session, lambda: world.platform_check().run(needs(world.admin.id))
    )
    record = world.team.list_team()[0]
    # Someone else holds SUPER, so the lists do not bring the admin back.
    add_admin(world, "boss@example.com", PlatformAdminRole.SUPER)
    world.team.delete(record.id)

    assert allowed.id == world.admin.id
    # Still flagged as admin in storage: the flag is not trusted.
    assert world.admin.is_platform_admin is True
    with pytest.raises(AccessDeniedError):
        world.in_request(
            session, lambda: world.platform_check().run(needs(world.admin.id))
        )
    business = BusinessAccessRequest(
        user_id=world.admin.id, business_id=world.business.id
    )
    open_support_session(world.grants, world.business.id, world.admin.id, NOW)
    with pytest.raises(NotFoundError):
        world.in_request(session, lambda: world.business_check().run(business))


def test_a_role_opens_only_its_own_pages() -> None:
    world = World()
    session = signed_in(world.admin.id)
    assert world.admins.role_of(world.admin) is PlatformAdminRole.SUPER
    add_admin(world, "boss@example.com", PlatformAdminRole.SUPER)
    record = next(a for a in world.team.list_team() if a.email == world.admin.email)
    world.team.save(record.model_copy(update={"role": PlatformAdminRole.BILLING}))
    check = world.platform_check()

    metrics = world.in_request(
        session,
        lambda: check.run(needs(world.admin.id, PlatformAdminPermission.VIEW_METRICS)),
    )

    assert metrics.id == world.admin.id
    for refused in (
        PlatformAdminPermission.OPEN_CLIENT_CABINET,
        PlatformAdminPermission.MANAGE_ADMINS,
        PlatformAdminPermission.MANAGE_OPERATIONS,
    ):
        request = needs(world.admin.id, refused)
        with pytest.raises(AccessDeniedError):
            world.in_request(session, partial(check.run, request))


def test_admin_access_needs_a_session_with_two_factors() -> None:
    world = World()
    one_factor = signed_in(world.admin.id, AuthLevel.ONE_FACTOR)
    someone_else = signed_in(UserId())
    business = BusinessAccessRequest(
        user_id=world.admin.id, business_id=world.business.id
    )
    open_support_session(world.grants, world.business.id, world.admin.id, NOW)

    with pytest.raises(MfaRequiredError):
        world.in_request(
            one_factor, lambda: world.platform_check().run(needs(world.admin.id))
        )
    with pytest.raises(MfaRequiredError):
        world.in_request(
            someone_else, lambda: world.platform_check().run(needs(world.admin.id))
        )
    with pytest.raises(NotFoundError):
        world.in_request(one_factor, lambda: world.business_check().run(business))
    # Outside a request (no session bound) the admin page check refuses too.
    with pytest.raises(MfaRequiredError):
        world.platform_check().run(needs(world.admin.id))
    # Background work acts on what a request already authorized (a live grant).
    assert world.business_check().run(business).id == world.business.id
