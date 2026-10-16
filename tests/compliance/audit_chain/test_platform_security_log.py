"""
The platform's security log (`GET /v1/admin/audit-log`): only admins who
may read it (not read-only support) see every person's sign-ins with their
addresses, and it holds every entry that names no business, those written
before the hash chain too, newest first.
"""

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.access import PlatformAdminPermission, PlatformAdminRole
from app.schemas.constants.compliance import AuditAction, AuditSecurityEvent
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.audit_chain_views import (
    AdminAuditChainsQuery,
    PlatformAuditLogPage,
    PlatformAuditLogQuery,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditChainPosition
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.use_cases.admin.audit.get_audit_chain_overview_use_case import (
    GetAuditChainOverviewUseCase,
)
from app.use_cases.admin.audit.list_platform_audit_log_use_case import (
    ListPlatformAuditLogUseCase,
)
from app.utilities.security.admin_permissions import has_permission
from tests.admin_actions.role_authorizer import RoleAuthorizer
from tests.compliance.audit_chain.audit_entries import entry
from tests.compliance.audit_trail_store import AuditTrailStore


class SecurityLogWorld:
    """One admin of a chosen role, the audit log and the two admin views."""

    def __init__(self, role: PlatformAdminRole) -> None:
        self.store = AuditTrailStore()
        users = UserRepository(
            InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
        )
        self.admin = UserDocument(
            login_method=LoginMethod.EMAIL,
            email=EmailAddress("admin@example.com"),
            locale=LanguageTag("en"),
            is_verified=True,
            is_platform_admin=True,
        )
        users.save(self.admin)
        authorize = RoleAuthorizer(users)
        authorize.roles[self.admin.id] = role
        self.log = ListPlatformAuditLogUseCase(authorize, self.store.activity)
        self.chains = GetAuditChainOverviewUseCase(authorize, self.store.chains)

    def page(self, **query: object) -> PlatformAuditLogPage:
        return self.log.run(
            PlatformAuditLogQuery.model_validate({"user_id": self.admin.id, **query})
        )


def unchained(minute: float, action: AuditAction) -> AuditLogEntryDocument:
    """What the release before 1193 stored: an entry with no chain fields."""

    return entry(None, minute, action=action, entity="user")


@pytest.mark.parametrize(
    "role", [PlatformAdminRole.SUPPORT_READONLY, PlatformAdminRole.BILLING]
)
def test_only_admins_who_may_read_it_see_the_security_log(
    role: PlatformAdminRole,
) -> None:
    world = SecurityLogWorld(role)

    with pytest.raises(AccessDeniedError):
        world.page()

    assert not has_permission(role, PlatformAdminPermission.VIEW_SECURITY_LOG)


def test_read_only_support_still_sees_the_tamper_check_of_the_chains() -> None:
    world = SecurityLogWorld(PlatformAdminRole.SUPPORT_READONLY)

    overview = world.chains.run(AdminAuditChainsQuery(user_id=world.admin.id))

    assert overview.platform.status is None


def test_entries_from_before_the_chain_are_in_the_log_newest_first() -> None:
    world = SecurityLogWorld(PlatformAdminRole.SUPER)
    old_change = unchained(1, AuditAction.MFA_CHANGED)
    old_revocation = unchained(2, AuditAction.SESSION_REVOKED)
    for stored in (old_change, old_revocation):
        assert world.store.entries.insert_if_absent(str(stored.id), stored)
    failed = entry(None, 3, action=AuditAction.LOGIN, entity="login_destination")
    world.store.log.append(
        failed.model_copy(update={"security_event": AuditSecurityEvent.LOGIN_FAILED})
    )
    world.store.log.append(entry(None, 4, action=AuditAction.SESSION_REVOKED))
    world.store.log.append(entry(BusinessId(), 5))  # A business's: not here.

    first = world.page(page=PageRequest(size=PageSize(2)))
    rest = world.page(page=PageRequest(size=PageSize(2), cursor=first.next_cursor))
    revocations = world.page(action=AuditAction.SESSION_REVOKED)

    listed = [*first.items, *rest.items]
    assert [item.occurred_at for item in listed] == sorted(
        (item.occurred_at for item in listed), reverse=True
    )
    assert [item.id for item in listed][2:] == [old_revocation.id, old_change.id]
    assert [item.chain_position for item in listed][:2] == [
        AuditChainPosition(2),
        AuditChainPosition(1),
    ]
    assert rest.next_cursor is None
    assert [item.chain_position for item in revocations.items] == [
        AuditChainPosition(2),
        None,
    ]
