"""
Admin rights are read from the PLATFORM_ADMIN_* lists at every check: an
admin taken off the lists is refused at the next request although the
stored flag (refreshed only at sign-in) still says admin; a session
without two factors never opens admin access.
"""

from collections.abc import Callable
from contextvars import copy_context

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.business_repositories import BusinessRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.application_errors import AccessDeniedError, NotFoundError
from app.schemas.exceptions.mfa_errors import MfaRequiredError
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.authorize_platform_admin_use_case import (
    AuthorizePlatformAdminUseCase,
)
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.foundation.access_support import (
    PLATFORM_ADMIN_EMAIL,
    platform_admin,
    settings_with_admins,
    signed_in,
)
from tests.foundation.builders import build_business
from tests.storage.storage_testing import build_fixed_wall_clock

LISTED: AppSettings = settings_with_admins([PLATFORM_ADMIN_EMAIL])
DELISTED: AppSettings = settings_with_admins()


class World:
    def __init__(self) -> None:
        self.users = UserRepository(InMemoryDocumentCollectionAdapter(UserDocument))
        self.businesses = BusinessRepository(
            InMemoryDocumentCollectionAdapter(BusinessDocument)
        )
        self.audit_entries = InMemoryDocumentCollectionAdapter(AuditLogEntryDocument)
        self.sessions = SessionAssuranceContext()
        self.admin: UserDocument = platform_admin()
        self.users.save(self.admin)
        self.business: BusinessDocument = build_business(UserId())
        self.businesses.save(self.business)

    def platform_check(self, settings: AppSettings) -> AuthorizePlatformAdminUseCase:
        return AuthorizePlatformAdminUseCase(self.users, self.sessions, settings)

    def business_check(self, settings: AppSettings) -> AuthorizeBusinessAccessUseCase:
        return AuthorizeBusinessAccessUseCase(
            business_repo=self.businesses,
            user_repo=self.users,
            audit_log_repo=AuditLogRepository(self.audit_entries),
            wall_clock=build_fixed_wall_clock(),
            session_assurance=self.sessions,
            app_settings=settings,
        )

    def in_request[T](self, assurance: SessionAssurance, work: Callable[[], T]) -> T:
        """Run `work` as a request of this session (its own context)."""

        def request() -> T:
            self.sessions.bind(assurance)
            return work()

        return copy_context().run(request)


def test_an_admin_taken_off_the_lists_is_refused_at_the_next_request() -> None:
    world = World()
    session = signed_in(world.admin.id)
    business = BusinessAccessRequest(
        user_id=world.admin.id, business_id=world.business.id
    )

    allowed = world.in_request(
        session, lambda: world.platform_check(LISTED).run(world.admin.id)
    )
    helped = world.in_request(
        session, lambda: world.business_check(LISTED).run(business)
    )

    assert allowed.id == world.admin.id
    assert helped.id == world.business.id
    assert [entry.action for entry in world.audit_entries.list_all()] == [
        AuditAction.ADMIN_ACCESS
    ]
    # Still flagged as admin in storage: the flag is not trusted.
    assert world.admin.is_platform_admin is True
    with pytest.raises(AccessDeniedError):
        world.in_request(
            session, lambda: world.platform_check(DELISTED).run(world.admin.id)
        )
    with pytest.raises(NotFoundError):
        world.in_request(session, lambda: world.business_check(DELISTED).run(business))


def test_admin_access_needs_a_session_with_two_factors() -> None:
    world = World()
    one_factor = signed_in(world.admin.id, AuthLevel.ONE_FACTOR)
    someone_else = signed_in(UserId())
    business = BusinessAccessRequest(
        user_id=world.admin.id, business_id=world.business.id
    )

    with pytest.raises(MfaRequiredError):
        world.in_request(
            one_factor, lambda: world.platform_check(LISTED).run(world.admin.id)
        )
    with pytest.raises(MfaRequiredError):
        world.in_request(
            someone_else, lambda: world.platform_check(LISTED).run(world.admin.id)
        )
    with pytest.raises(NotFoundError):
        world.in_request(one_factor, lambda: world.business_check(LISTED).run(business))
    # Outside a request (no session bound) the admin page check refuses too.
    with pytest.raises(MfaRequiredError):
        world.platform_check(LISTED).run(world.admin.id)
    # Background work acts on what a request already authorized.
    assert world.business_check(LISTED).run(business).id == world.business.id
