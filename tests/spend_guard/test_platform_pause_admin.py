"""
The global pause: only a SUPER platform admin pauses or resumes every
assistant, after a recent sign-in, with a reason the platform's audit log
keeps; every admin who sees operations reads how the brakes stand.
"""

import pytest

from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.spend import PlatformBrake
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.dto.platform_pause import (
    PlatformPauseCommand,
    PlatformPauseQuery,
    PlatformPauseRequest,
)
from app.schemas.exceptions.application_errors import AccessDeniedError, ConflictError
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    UsageQuantity,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.spend.constrained_integers import (
    PlatformDailySpendBudgetMicroUsd,
)
from app.schemas.typings.spend.constrained_strings import PlatformPauseReason
from app.schemas.typings.users.prefixed_id import UserId
from tests.spend_guard.platform_pause_world import NOW, PauseWorld

REASON: PlatformPauseReason = PlatformPauseReason("Model answers in the wrong language")


def command(user_id: UserId, is_paused: bool) -> PlatformPauseCommand:
    return PlatformPauseCommand(
        user_id=user_id,
        request=PlatformPauseRequest(is_paused=is_paused, reason=REASON),
        client_ip_address=ClientIpAddress("203.0.113.7"),
    )


def test_a_super_admin_pauses_and_resumes_every_assistant_with_audit() -> None:
    world = PauseWorld()

    paused = world.set_use_case().run(command(world.super_admin, True))

    assert paused.is_paused and paused.brake is PlatformBrake.PAUSED
    assert paused.reason == REASON and paused.changed_by == world.super_admin
    assert paused.changed_at == NOW
    resumed = world.set_use_case().run(command(world.super_admin, False))
    assert not resumed.is_paused and resumed.brake is None

    entries = world.platform_entries()
    assert [(e.action, str(e.entity), str(e.entity_id)) for e in entries] == [
        (AuditAction.UPDATE, "platform_pause", "paused"),
        (AuditAction.UPDATE, "platform_pause", "resumed"),
    ]
    assert {str(e.reason) for e in entries} == {str(REASON)}
    assert {e.actor_id for e in entries} == {world.super_admin}
    assert {str(e.ip_address) for e in entries} == {"203.0.113.7"}
    assert all(e.business_id is None for e in entries)


def test_pausing_twice_or_resuming_a_running_platform_is_a_conflict() -> None:
    world = PauseWorld()

    with pytest.raises(ConflictError):
        world.set_use_case().run(command(world.super_admin, False))
    world.set_use_case().run(command(world.super_admin, True))
    with pytest.raises(ConflictError):
        world.set_use_case().run(command(world.super_admin, True))
    assert len(world.platform_entries()) == 1


@pytest.mark.parametrize("who", ["support", "billing", "stranger"])
def test_only_a_super_admin_may_pause(who: str) -> None:
    world = PauseWorld()
    user_id: UserId = getattr(world, who) if who != "stranger" else UserId()

    with pytest.raises(AccessDeniedError):
        world.set_use_case().run(command(user_id, True))

    assert world.pauses.get() is None
    assert world.platform_entries() == []


def test_pausing_needs_a_recent_sign_in() -> None:
    world = PauseWorld()
    world.step_up.is_recent = False

    with pytest.raises(StepUpRequiredError):
        world.set_use_case().run(command(world.super_admin, True))

    assert world.pauses.get() is None


def test_support_reads_the_brakes_with_the_budget_stop() -> None:
    world = PauseWorld(
        settings=SpendGuardSettings(
            platform_daily_budget_micro_usd=PlatformDailySpendBudgetMicroUsd(20_000_000)
        )
    )
    world.usage_events.upsert(
        "spent",
        UsageEventDocument(
            business_id=BusinessId(),
            kind=UsageKind.LLM_OUTPUT_TOKENS,
            quantity=UsageQuantity(9_000),
            cost_micro_usd=CostMicroUsd(25_000_000),
            occurred_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        ),
    )

    view = world.get_use_case().run(PlatformPauseQuery(user_id=world.support))

    assert not view.is_paused and view.reason is None
    assert int(view.stop_percent) == 100
    assert view.budget_used_percent is not None
    assert int(view.budget_used_percent) == 125
    assert view.brake is PlatformBrake.BUDGET_STOP
    with pytest.raises(AccessDeniedError):
        world.get_use_case().run(PlatformPauseQuery(user_id=world.billing))
