"""The platform admin's review of campaigns held over their opt-out rate (ABUSE-05)."""

import pytest

from app.repositories.compliance_repositories import AuditLogRepository
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin_campaign_holds import (
    ListCampaignHoldsQuery,
    ReleaseCampaignHoldCommand,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
)
from app.schemas.typings.access.constrained_strings import AdminActionReason
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.abuse.list_campaign_holds_use_case import (
    ListCampaignHoldsUseCase,
)
from app.use_cases.admin.abuse.release_campaign_hold_use_case import (
    ReleaseCampaignHoldUseCase,
)
from tests.admin_actions.role_authorizer import RoleAuthorizer
from tests.campaigns.campaign_world import CampaignWorld
from tests.campaigns.test_campaign_opt_out_holds import build_gate, reach, settings_of
from tests.compliance.audit_repositories import audit_log_repository
from tests.invoicing.attachment_fakes import RecordingStaffNotifier

REASON: AdminActionReason = AdminActionReason("Agreed a consent-only segment.")


def admin_of(
    world: CampaignWorld, authorizer: RoleAuthorizer, role: PlatformAdminRole
) -> UserId:
    admin = UserDocument(
        id=UserId(),
        login_method=LoginMethod.EMAIL,
        email=EmailAddress(f"{role.value}@workshop.example"),
        locale=world.business.default_language,
        created_at=world.clock.now_microseconds(),
        updated_at=world.clock.now_microseconds(),
    )
    world.user_repo.save(admin)
    authorizer.roles[admin.id] = role
    return admin.id


def held_world() -> CampaignWorld:
    world = CampaignWorld()
    world.enable()
    reach(world, 40, stops=3)
    gate, _, _ = build_gate(world)
    gate.is_held(world.business, settings_of(world), world.clock.now_microseconds())
    return world


def test_an_admin_sees_the_held_campaigns() -> None:
    world = held_world()
    authorizer = RoleAuthorizer(world.user_repo)
    support = admin_of(world, authorizer, PlatformAdminRole.SUPPORT_READONLY)

    listed = ListCampaignHoldsUseCase(authorizer, world.campaign_settings_repo).run(
        ListCampaignHoldsQuery(user_id=support)
    )

    [hold] = listed.items
    assert hold.business_id == world.business.id
    assert (int(hold.sent), int(hold.opted_out)) == (40, 3)


def release_use_case(
    world: CampaignWorld, authorizer: RoleAuthorizer, audit_log: AuditLogRepository
) -> tuple[ReleaseCampaignHoldUseCase, RecordingStaffNotifier]:
    notifier = RecordingStaffNotifier()
    use_case = ReleaseCampaignHoldUseCase(
        authorize_platform_admin=authorizer,
        business_repo=world.business_repo,
        campaign_settings_repo=world.campaign_settings_repo,
        user_repo=world.user_repo,
        manager_notifier=notifier,
        text_resolver=world.resolver,
        audit_log_repo=audit_log,
        wall_clock=world.clock.wall_clock,
    )
    return use_case, notifier


def test_a_super_admin_releases_a_hold_with_an_audit_entry_and_a_notice() -> None:
    world = held_world()
    audit_log = audit_log_repository()
    authorizer = RoleAuthorizer(world.user_repo)
    super_admin = admin_of(world, authorizer, PlatformAdminRole.SUPER)
    use_case, notifier = release_use_case(world, authorizer, audit_log)

    use_case.run(
        ReleaseCampaignHoldCommand(
            user_id=super_admin,
            business_id=world.business.id,
            reason=REASON,
            client_ip_address=ClientIpAddress("203.0.113.9"),
        )
    )

    assert settings_of(world).review_hold is None
    [entry] = audit_log.list_by_business(world.business.id)
    assert (entry.action, str(entry.entity_id)) == (
        AuditAction.UPDATE,
        "review_hold_released",
    )
    assert entry.reason == REASON and entry.actor_id == super_admin
    [notice] = notifier.notifications
    assert "writes to your customers again" in str(notice.text) or "torna a" in str(
        notice.text
    )
    with pytest.raises(ConflictError):
        use_case.run(
            ReleaseCampaignHoldCommand(
                user_id=super_admin, business_id=world.business.id, reason=REASON
            )
        )


def test_only_a_super_admin_may_release_a_hold() -> None:
    world = held_world()
    authorizer = RoleAuthorizer(world.user_repo)
    support = admin_of(world, authorizer, PlatformAdminRole.SUPPORT_READONLY)
    use_case, _ = release_use_case(world, authorizer, audit_log_repository())

    with pytest.raises(AccessDeniedError):
        use_case.run(
            ReleaseCampaignHoldCommand(
                user_id=support, business_id=world.business.id, reason=REASON
            )
        )

    assert settings_of(world).review_hold is not None
