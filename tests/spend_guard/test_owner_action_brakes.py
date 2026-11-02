"""
The owners' costly actions while a platform brake holds: a menu import, an
autotest run, alias suggestions and a rented number are refused (409,
reason `platform_brake`) and not counted; the test chat, number searches
and requests for a number pass. `PlatformBrakeRegistry` reads the pause
and the daily budget stop as the spend guard does.
"""

from datetime import timedelta

import pytest

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.registries.limits.platform_brake_registry import PlatformBrakeRegistry
from app.registries.limits.platform_spend_gauge_registry import (
    PlatformSpendGaugeRegistry,
)
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.schemas.constants.spend import OwnerAction, PlatformBrake
from app.schemas.dto.spend_guard import OwnerActionAdmission
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.spend_guard.admit_owner_action_use_case import (
    BRAKED_ACTIONS,
    AdmitOwnerActionUseCase,
    CheckOwnerActionRoomUseCase,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.spend_guard.platform_brake_fakes import SetPlatformBrakes
from tests.spend_guard.platform_brake_helpers import (
    budget_settings,
    pause,
    spend_elsewhere,
)
from tests.spend_guard.request_limit_app import MovingClock
from tests.spend_guard.spend_world import DOLLAR, NOON, build_spend_world, micros

COSTLY: list[OwnerAction] = [
    OwnerAction.MENU_IMPORT,
    OwnerAction.AUTOTEST_RUN,
    OwnerAction.ALIAS_SUGGESTION,
    OwnerAction.PHONE_NUMBER_RENTAL,
]
FREE: list[OwnerAction] = [
    OwnerAction.TEST_CHAT,
    OwnerAction.PHONE_NUMBER_SEARCH,
    OwnerAction.PHONE_NUMBER_REQUEST,
]


def admission(action: OwnerAction) -> OwnerActionAdmission:
    return OwnerActionAdmission(
        action=action, user_id=UserId(), business_id=BusinessId()
    )


def build(
    brakes: SetPlatformBrakes,
) -> tuple[AdmitOwnerActionUseCase, CheckOwnerActionRoomUseCase]:
    clock = MovingClock()
    rate_limits = RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter())
    return (
        AdmitOwnerActionUseCase(rate_limits, brakes, clock.wall_clock),
        CheckOwnerActionRoomUseCase(rate_limits, brakes, clock.wall_clock),
    )


def test_the_braked_actions_are_the_costly_ones() -> None:
    assert sorted(BRAKED_ACTIONS) == sorted(COSTLY)
    assert set(COSTLY) | set(FREE) == set(OwnerAction)


@pytest.mark.parametrize("brake", list(PlatformBrake))
@pytest.mark.parametrize("action", COSTLY)
def test_a_costly_action_is_refused_while_a_brake_holds_and_not_counted(
    brake: PlatformBrake, action: OwnerAction
) -> None:
    brakes = SetPlatformBrakes(brake)
    admit, check_room = build(brakes)
    asked = admission(action)

    for use_case in (admit, check_room):
        with pytest.raises(ConflictError) as refusal:
            use_case.run(asked)
        [reason] = refusal.value.reasons
        assert str(reason.code) == "platform_brake"
        assert [str(detail) for detail in reason.details] == [brake.value]

    brakes.brake = None
    # Nothing was counted while refused: the whole limit is still there.
    if action is OwnerAction.PHONE_NUMBER_RENTAL:
        for _ in range(3):
            check_room.run(asked)
            admit.run(asked)
    else:
        admit.run(asked)


@pytest.mark.parametrize("action", FREE)
def test_free_actions_pass_whatever_the_brake(action: OwnerAction) -> None:
    brakes = SetPlatformBrakes(PlatformBrake.PAUSED)
    admit, check_room = build(brakes)

    check_room.run(admission(action))
    admit.run(admission(action))

    assert brakes.readings == []


def test_the_registry_reads_the_pause_and_the_budget_stop() -> None:
    world = build_spend_world(settings=budget_settings(100))
    gauge = PlatformSpendGaugeRegistry(world.usage_spend, StorageScopeContext())
    registry = PlatformBrakeRegistry(world.pauses, gauge, budget_settings(100))
    noon = micros(NOON)

    calm = registry.current_brake(noon)
    pause(world)
    paused = registry.current_brake(noon)
    pause(world, is_paused=False)
    spend_elsewhere(world, 100 * DOLLAR)
    stopped = registry.current_brake(micros(NOON + timedelta(minutes=2)))

    assert (calm, paused, stopped) == (
        None,
        PlatformBrake.PAUSED,
        PlatformBrake.BUDGET_STOP,
    )
