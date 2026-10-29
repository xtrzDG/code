"""At most four paused months in any twelve, whatever way the pauses ended."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.subscription_lifecycle import (
    PauseUnavailableReason,
    SubscriptionEventKind,
)
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.billing.prefixed_id import SubscriptionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.billing.billing_periods import add_calendar_months
from app.utilities.billing.pause_allowance import (
    max_pause_months,
    months_paused_before,
    pause_spans,
)
from tests.subscription_lifecycle.lifecycle_world import LifecycleWorld
from tests.subscription_lifecycle.pause_steps import (
    HOUR_MICROSECONDS,
    pause,
    reach_pause_start,
    resume,
)

TBILISI = TimezoneName("Asia/Tbilisi")
JANUARY = Microseconds(1_767_211_200_000_000)  # 2026-01-01 00:00 in Tbilisi
BUSINESS = BusinessId()
SUBSCRIPTION = SubscriptionId()


def month(index: int) -> Microseconds:
    return add_calendar_months(JANUARY, index, TBILISI)


def step(
    kind: SubscriptionEventKind,
    starts: Microseconds,
    until: Microseconds,
    at: Microseconds,
) -> SubscriptionEventDocument:
    return SubscriptionEventDocument(
        business_id=BUSINESS,
        subscription_id=SUBSCRIPTION,
        kind=kind,
        occurred_at=at,
        pause_starts_at=starts,
        pause_until=until,
        created_at=at,
        updated_at=at,
    )


def scheduled(start: int, months: int, at: int = -1) -> SubscriptionEventDocument:
    """Scheduled at month `at` (before the start)."""

    return step(
        SubscriptionEventKind.PAUSE_SCHEDULED,
        month(start),
        month(start + months),
        month(min(at, start - 1)),
    )


def resumed(start: int, ended: int, at: int | None = None) -> SubscriptionEventDocument:
    """Ended at month `ended` (the step written at month `at`, else then)."""

    return step(
        SubscriptionEventKind.RESUMED,
        month(start),
        month(ended),
        month(ended if at is None else at),
    )


def allowed(events: list[SubscriptionEventDocument], start: int) -> int:
    return max_pause_months(events, month(start), TBILISI, 4, 12)


def test_four_months_fit_a_business_that_never_paused() -> None:
    assert allowed([], 0) == 4


def test_the_cap_counts_the_months_of_the_last_twelve() -> None:
    three_months = [scheduled(0, 3), resumed(0, 3)]

    assert allowed(three_months, 5) == 1
    # One more month fits; a second would make five within months 0 to 11.
    assert allowed(three_months, 9) == 1
    # From month 11 every window of twelve holds at most four.
    assert allowed(three_months, 11) == 4
    assert months_paused_before(three_months, month(5), TBILISI, 12) == 3


def test_four_months_used_leave_nothing_until_a_year_after_they_began() -> None:
    events = [scheduled(0, 4), resumed(0, 4)]

    assert allowed(events, 6) == 0
    assert allowed(events, 11) == 0
    assert allowed(events, 12) == 4


def test_a_pause_called_off_before_it_started_counts_nothing() -> None:
    events = [scheduled(2, 4, at=0), resumed(2, 2, at=1)]

    assert pause_spans(events) == [(month(2), month(2))]
    assert allowed(events, 3) == 4


def test_a_pause_ended_early_counts_the_months_it_began() -> None:
    events = [scheduled(0, 4), resumed(0, 2)]

    assert allowed(events, 3) == 2


def test_a_pause_scheduled_again_from_the_same_start_counts_once() -> None:
    events = [scheduled(1, 2, at=-2), resumed(1, 1, at=-1), scheduled(1, 3, at=0)]

    assert sorted(pause_spans(events)) == [(month(1), month(1)), (month(1), month(4))]
    assert allowed(events, 5) == 1


def test_the_owner_cannot_pause_beyond_the_cap() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()

    pause(world, owner, business, months=4)
    with pytest.raises(ConflictError):
        pause(world, owner, business, months=1)

    pause_view = world.lifecycle_of(business).pause
    assert pause_view.unavailable_reason is PauseUnavailableReason.ALREADY_PAUSED


def test_a_second_pause_in_the_year_gets_what_the_cap_leaves() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()
    pause(world, owner, business, months=3)
    reach_pause_start(world, business)
    pause_until = world.current(business).pause_until
    assert pause_until is not None
    world.clock.move_to(Microseconds(int(pause_until) + HOUR_MICROSECONDS))
    world.run_pause_job()
    # Pay the first full month again, so the subscription is active and paid.
    world.clock.advance(days=1, hours=1)

    options = world.lifecycle_of(business).pause
    assert options.paused_months == 3
    assert options.max_months == 1
    with pytest.raises(ConflictError):
        pause(world, owner, business, months=2)

    pause(world, owner, business, months=1)
    resume(world, owner, business)
    assert world.lifecycle_of(business).pause.max_months == 1
