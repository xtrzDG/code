"""
The cabinet actions that make the platform pay a provider are limited:
test chat messages per person, menu imports and autotest runs per business
(one version under test at a time).
"""

import pytest

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.schemas.constants.spend import OwnerAction
from app.schemas.dto.assistants.assistant_commands import RunAutotestsCommand
from app.schemas.dto.spend_guard import OwnerActionAdmission
from app.schemas.exceptions.application_errors import ConflictError, RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.spend_guard.admit_owner_action_use_case import (
    AdmitOwnerActionUseCase,
)
from tests.assembly.autotest_run_helpers import start
from tests.assembly.testbed import AssemblyTestbed
from tests.spend_guard.request_limit_app import MovingClock

MINUTE: int = 60 * 1_000_000
HOUR: int = 60 * MINUTE
DAY: int = 24 * HOUR
OWNER: UserId = UserId()
BUSINESS: BusinessId = BusinessId()


def admit_until_refused(
    admit: AdmitOwnerActionUseCase,
    action: OwnerAction,
    user_id: UserId = OWNER,
    business_id: BusinessId = BUSINESS,
) -> tuple[int, RateLimitedError]:
    """How many actions pass before the first refusal, and the refusal."""

    admitted = 0
    while True:
        try:
            admit.run(
                OwnerActionAdmission(
                    action=action, user_id=user_id, business_id=business_id
                )
            )
        except RateLimitedError as refusal:
            return admitted, refusal
        admitted += 1


def build_admit() -> tuple[AdmitOwnerActionUseCase, MovingClock]:
    clock = MovingClock()
    admit = AdmitOwnerActionUseCase(
        RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter()), clock.wall_clock
    )
    return admit, clock


def test_a_person_sends_thirty_test_messages_a_minute() -> None:
    admit, clock = build_admit()

    admitted, refusal = admit_until_refused(admit, OwnerAction.TEST_CHAT)

    assert admitted == 30
    assert "test messages" in str(refusal)
    assert refusal.retry_after_seconds is not None
    assert 1 <= int(refusal.retry_after_seconds) <= 120
    # Another person of the same business has a limit of their own.
    assert admit_until_refused(admit, OwnerAction.TEST_CHAT, UserId())[0] == 30
    clock.now += 2 * MINUTE
    assert admit_until_refused(admit, OwnerAction.TEST_CHAT)[0] == 30


def test_a_business_imports_ten_menus_an_hour_whoever_imports_them() -> None:
    admit, _ = build_admit()

    admitted, refusal = admit_until_refused(admit, OwnerAction.MENU_IMPORT)
    other_person, _ = admit_until_refused(admit, OwnerAction.MENU_IMPORT, UserId())
    other_business, _ = admit_until_refused(
        admit, OwnerAction.MENU_IMPORT, business_id=BusinessId()
    )

    assert (admitted, other_person, other_business) == (10, 0, 10)
    assert refusal.retry_after_seconds is not None
    assert int(refusal.retry_after_seconds) > 60


def test_a_business_starts_twenty_autotest_runs_a_day() -> None:
    admit, clock = build_admit()

    admitted, refusal = admit_until_refused(admit, OwnerAction.AUTOTEST_RUN)

    assert admitted == 20
    assert "20 times a day" in str(refusal)
    clock.now += 2 * DAY
    assert admit_until_refused(admit, OwnerAction.AUTOTEST_RUN)[0] == 20


def test_a_business_tests_one_version_at_a_time() -> None:
    testbed = AssemblyTestbed()
    business, first = start(testbed)
    second = testbed.assemble(business.id)
    testbed.queue_autotest_run_orchestrator.execute(
        RunAutotestsCommand(
            user_id=testbed.owner_id, business_id=business.id, version_id=first.id
        )
    )

    with pytest.raises(ConflictError, match="Another version is being tested"):
        testbed.queue_autotest_run_orchestrator.execute(
            RunAutotestsCommand(
                user_id=testbed.owner_id, business_id=business.id, version_id=second.id
            )
        )
