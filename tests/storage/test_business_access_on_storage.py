"""
Access to a business on in-memory and on Postgres storage: owners, staff,
strangers, and platform support during an open look into the cabinet
(read-only unless the owner allowed changes). Runs twice through the
`collections` fixture.
"""

import pytest

from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.repositories.business_repositories import BusinessRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.platform_admin_repository import PlatformAdminRepository
from app.repositories.support_access_grant_repository import (
    SupportAccessGrantRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.exceptions.application_errors import AccessDeniedError, NotFoundError
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.foundation.access_support import ACCESS_SETTINGS, PLATFORM_ADMIN_EMAIL
from tests.foundation.support_access_builders import (
    allow_support_changes,
    build_authorize_business_access,
    in_memory_platform_admins,
    open_support_session,
)
from tests.storage.builders import (
    COUNTRY_SAMPLES,
    build_business,
    build_email_user,
    build_owner,
)
from tests.storage.conftest import CollectionFactory
from tests.storage.storage_testing import FIXED_NANOSECONDS, build_fixed_wall_clock

# Seeding and checking rows of several businesses runs platform-wide; the
# business scopes a test enters nest inside (tests/storage/conftest.py).
pytestmark = pytest.mark.usefixtures("platform_scope")

ISRAEL, EMIRATES = COUNTRY_SAMPLES[1], COUNTRY_SAMPLES[2]
NOW_MICROSECONDS: int = FIXED_NANOSECONDS // 1_000


def test_business_access_for_owner_staff_stranger_and_admin(
    collections: CollectionFactory,
) -> None:
    business_repo = BusinessRepository(collections(BusinessDocument, "businesses"))
    user_repo = UserRepository(collections(UserDocument, "users"))
    audit_log_repo = AuditLogRepository(
        collections(AuditLogEntryDocument, "audit_log_entries")
    )
    grant_repo = SupportAccessGrantRepository(
        collections(SupportAccessGrantDocument, "support_access_grants")
    )
    wall_clock = build_fixed_wall_clock()
    operator = PipelineOperator(
        OrchestratorPipeline(
            UseCaseOrchestrator(
                build_authorize_business_access(
                    business_repo=business_repo,
                    user_repo=user_repo,
                    audit_log_repo=audit_log_repo,
                    wall_clock=wall_clock,
                    session_assurance=SessionAssuranceContext(),
                    app_settings=ACCESS_SETTINGS,
                    grant_repo=grant_repo,
                    platform_admins=in_memory_platform_admins(
                        wall_clock,
                        ACCESS_SETTINGS,
                        PlatformAdminRepository(
                            collections(PlatformAdminDocument, "platform_admins")
                        ),
                    ),
                )
            )
        )
    )
    owner, staff = build_owner(ISRAEL), build_owner(EMIRATES)
    business = build_business(ISRAEL, owner.id)
    business.members.append(
        BusinessMember(user_id=staff.id, role=BusinessMemberRole.STAFF)
    )
    admin = build_email_user(PLATFORM_ADMIN_EMAIL, "ru")
    admin.is_platform_admin = True
    for user in (owner, staff, admin):
        user_repo.save(user)
    business_repo.save(business)

    owner_request = BusinessAccessRequest(
        user_id=owner.id,
        business_id=business.id,
        required_role=BusinessMemberRole.OWNER,
    )
    assert operator.operate(owner_request).id == business.id
    assert (
        operator.operate(
            BusinessAccessRequest(user_id=staff.id, business_id=business.id)
        ).name
        == ISRAEL.business_name
    )
    with pytest.raises(AccessDeniedError):
        operator.operate(
            BusinessAccessRequest(
                user_id=staff.id,
                business_id=business.id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
    with pytest.raises(NotFoundError):
        operator.operate(
            BusinessAccessRequest(user_id=UserId(), business_id=business.id)
        )
    # Platform support: only during an open look, reading unless the owner
    # allowed changes; each change is audited.
    support = BusinessAccessRequest(user_id=admin.id, business_id=business.id)
    change = support.model_copy(update={"access_mode": BusinessAccessMode.WRITE})
    with pytest.raises(AccessDeniedError):
        operator.operate(support)
    open_support_session(grant_repo, business.id, admin.id, NOW_MICROSECONDS)
    assert operator.operate(support).id == business.id
    with pytest.raises(AccessDeniedError):
        operator.operate(change)
    allow_support_changes(grant_repo, business.id, owner.id, NOW_MICROSECONDS)
    assert operator.operate(change).id == business.id
    entries = audit_log_repo.list_by_business(business.id)
    assert [entry.action for entry in entries] == [AuditAction.ADMIN_ACCESS]
    assert entries[0].actor_id == admin.id
    assert [found.id for found in business_repo.list_by_member(staff.id)] == [
        business.id
    ]
