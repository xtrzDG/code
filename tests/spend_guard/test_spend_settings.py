"""
The lists and limits people change: the owner's allowed chat websites, the
admin's spend tile and a client's own spend limits.
"""

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.use_case_contract import UseCaseContract
from app.repositories.business_repositories import BusinessRepository
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.spend import SpendLevel, SpendProvider
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.spend_guard import (
    AdminSpendQuery,
    BusinessSpendLimitsCommand,
    BusinessSpendLimitsRequest,
    SpendCheckRequest,
)
from app.schemas.dto.widget_origins import (
    SaveWidgetAllowedOriginsCommand,
    WidgetAllowedOriginsQuery,
    WidgetAllowedOriginsRequest,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.spend.constrained_integers import (
    DailySpendLimitMicroUsd,
    PlatformDailySpendBudgetMicroUsd,
)
from app.schemas.typings.spend.constrained_strings import WidgetSiteAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.spend.get_platform_spend_use_case import (
    GetPlatformSpendUseCase,
)
from app.use_cases.admin.spend.set_business_spend_limits_use_case import (
    SetBusinessSpendLimitsUseCase,
)
from app.use_cases.spend_guard.get_widget_allowed_origins_use_case import (
    GetWidgetAllowedOriginsUseCase,
)
from app.use_cases.spend_guard.save_widget_allowed_origins_use_case import (
    SaveWidgetAllowedOriginsUseCase,
)
from tests.platform_ops.ops_world import ADMIN, AdminsOnly
from tests.spend_guard.request_limit_app import MovingClock
from tests.spend_guard.spend_world import DOLLAR, NOON, SpendWorld, micros
from tests.spend_guard.spend_world import build_spend_world as build_world

CABINET: list[PublicBaseUrl] = [PublicBaseUrl("https://app.workshop.example")]
STAFF: UserId = UserId()


class TeamAccess(UseCaseContract[BusinessAccessRequest, BusinessDocument]):
    """Owners pass everything; staff only what any member may."""

    def __init__(self, business: BusinessDocument) -> None:
        self._business: BusinessDocument = business

    def run(self, input_data: BusinessAccessRequest) -> BusinessDocument:
        if input_data.user_id == STAFF and (
            input_data.required_role is BusinessMemberRole.OWNER
        ):
            raise AccessDeniedError("Owners only.")
        return self._business


def save_sites(world: SpendWorld, user_id: UserId, *sites: str) -> list[str]:
    view = SaveWidgetAllowedOriginsUseCase(
        TeamAccess(world.business), world.limits, CABINET, MovingClock().wall_clock
    ).run(
        SaveWidgetAllowedOriginsCommand(
            user_id=user_id,
            business_id=world.business.id,
            request=WidgetAllowedOriginsRequest(
                origins=[WidgetSiteAddress(site) for site in sites]
            ),
        )
    )
    return [str(origin) for origin in view.origins]


def test_the_owner_saves_sites_as_origins_once_per_site() -> None:
    world = build_world()

    saved = save_sites(
        world, world.owner.id, "cafe-batumi.ge/menu", "www.cafe-batumi.ge", "shop.ge"
    )
    view = GetWidgetAllowedOriginsUseCase(
        TeamAccess(world.business), world.limits, CABINET
    ).run(WidgetAllowedOriginsQuery(user_id=STAFF, business_id=world.business.id))

    assert saved == ["https://cafe-batumi.ge", "https://shop.ge"]
    assert [str(origin) for origin in view.origins] == saved
    assert view.is_restricted is True
    assert view.always_allowed == CABINET
    assert save_sites(world, world.owner.id) == []


def test_staff_may_read_the_sites_but_not_change_them() -> None:
    world = build_world()

    with pytest.raises(AccessDeniedError):
        save_sites(world, STAFF, "cafe.ge")


def test_an_address_that_is_no_website_is_refused() -> None:
    world = build_world()

    with pytest.raises(ValidationFailedError, match="not a website"):
        save_sites(world, world.owner.id, "cafe.ge", "my cafe")


def admin_spend(
    world: SpendWorld, budget: int | None = None
) -> GetPlatformSpendUseCase:
    businesses = BusinessRepository(InMemoryDocumentCollectionAdapter(BusinessDocument))
    businesses.save(world.business)
    clock = MovingClock()
    clock.now = int(micros(NOON))
    return GetPlatformSpendUseCase(
        AdminsOnly(),
        world.usage_spend,
        world.marks,
        businesses,
        SpendGuardSettings(
            platform_daily_budget_micro_usd=(
                None if budget is None else PlatformDailySpendBudgetMicroUsd(budget)
            )
        ),
        clock.wall_clock,
    )


def test_the_admin_tile_shows_todays_spend_by_provider_and_braked_businesses() -> None:
    world = build_world()
    world.set_limits(soft=DOLLAR, hard=10 * DOLLAR)
    world.spend(UsageKind.LLM_OUTPUT_TOKENS, 9_000, 2 * DOLLAR)
    world.spend(UsageKind.VOICE_SECONDS, 120, 300_000)
    world.check.run(SpendCheckRequest(business=world.business, now=micros(NOON)))

    view = admin_spend(world, budget=10 * DOLLAR).run(AdminSpendQuery(user_id=ADMIN))

    assert {item.provider: int(item.spend_micro_usd) for item in view.providers} == {
        SpendProvider.LANGUAGE_MODEL: 2 * DOLLAR,
        SpendProvider.VOICE: 300_000,
    }
    assert int(view.total_micro_usd) == 2_300_000
    assert view.budget_used_percent == 23
    (braked,) = view.braked_businesses
    assert (braked.business_name, braked.level) == (
        "Salobie Bia",
        SpendLevel.SOFT_LIMIT,
    )


def test_only_platform_admins_see_the_spend() -> None:
    world = build_world()

    with pytest.raises(AccessDeniedError):
        admin_spend(world).run(AdminSpendQuery(user_id=UserId()))


def test_an_admin_sets_a_clients_own_limits_on_its_audit_log() -> None:
    world = build_world()
    businesses = BusinessRepository(InMemoryDocumentCollectionAdapter(BusinessDocument))
    businesses.save(world.business)
    set_limits = SetBusinessSpendLimitsUseCase(
        AdminsOnly(), businesses, world.limits, world.audit, MovingClock().wall_clock
    )

    view = set_limits.run(
        BusinessSpendLimitsCommand(
            user_id=ADMIN,
            business_id=world.business.id,
            request=BusinessSpendLimitsRequest(
                hard_limit_micro_usd=DailySpendLimitMicroUsd(0)
            ),
        )
    )
    world.spend(UsageKind.DIALOG, 1, 0)
    verdict = world.check.run(
        SpendCheckRequest(business=world.business, now=micros(NOON))
    )

    assert (view.soft_limit_micro_usd, view.hard_limit_micro_usd) == (None, 0)
    # A hard limit of 0 brakes the assistant at once.
    assert verdict.level is SpendLevel.HARD_LIMIT
    actions = [entry.action for entry in world.audit_entries()]
    assert actions == [AuditAction.UPDATE, AuditAction.SPEND_LIMIT_REACHED]
    with pytest.raises(ValidationFailedError):
        set_limits.run(
            BusinessSpendLimitsCommand(
                user_id=ADMIN,
                business_id=world.business.id,
                request=BusinessSpendLimitsRequest(
                    soft_limit_micro_usd=DailySpendLimitMicroUsd(5),
                    hard_limit_micro_usd=DailySpendLimitMicroUsd(1),
                ),
            )
        )
