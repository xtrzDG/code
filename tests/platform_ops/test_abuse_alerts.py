"""
The booking abuse alerts (ABUSE-04): a business past 40 new bookings or 15
cancellations in an hour, counted where the change is announced and read
by the platform alerts job, once per business and hour however many
processes count at the same time.
"""

import pytest

from app.adapters.events.in_memory_live_event_bus_adapter import (
    InMemoryLiveEventBusAdapter,
)
from app.facilitators.events.event_publisher_facilitator import (
    EventPublisherFacilitator,
)
from app.facilitators.monitoring.booking_surge_observer_facilitator import (
    BOOKING_SURGE_PER_HOUR,
    CANCELLATION_SURGE_PER_HOUR,
    NEW_BOOKINGS_KEY,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.monitoring import PlatformAlertCode, PlatformSignal
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import RateWindowSeconds
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.limits.sliding_window_limits import locate_window
from app.utilities.monitoring.signal_windows import UNLIMITED
from tests.platform_ops.abuse_world import BookingWorld
from tests.platform_ops.ops_documents import HOUR

HOUR_WINDOW: RateWindowSeconds = RateWindowSeconds(60 * 60)


@pytest.fixture
def world() -> BookingWorld:
    return BookingWorld()


def test_forty_new_bookings_an_hour_stay_quiet(world: BookingWorld) -> None:
    world.announce(BusinessId(), LiveEventKind.BOOKING_CREATED, times=40)

    assert BOOKING_SURGE_PER_HOUR == 40
    assert world.signals(PlatformSignal.BOOKING_SURGE) == 0
    assert not world.observe(PlatformAlertCode.BOOKING_SPIKE).is_firing


def test_the_41st_new_booking_fires_the_alert_once(
    world: BookingWorld, caplog: pytest.LogCaptureFixture
) -> None:
    business_id = BusinessId()

    world.announce(business_id, LiveEventKind.BOOKING_CREATED, times=60)

    assert world.signals(PlatformSignal.BOOKING_SURGE) == 1
    observation = world.observe(PlatformAlertCode.BOOKING_SPIKE)
    assert observation.is_firing
    assert "past 40 new bookings" in str(observation.detail)
    # The log names the business, never a customer.
    assert f"Business {business_id} had more than 40 new bookings" in caplog.text


def test_new_bookings_count_per_business_and_hour(world: BookingWorld) -> None:
    world.announce(BusinessId(), LiveEventKind.BOOKING_CREATED, times=30)
    world.announce(BusinessId(), LiveEventKind.BOOKING_CREATED, times=30)
    world.ops.clock.advance(HOUR)
    world.announce(BusinessId(), LiveEventKind.BOOKING_CREATED, times=30)

    assert world.signals(PlatformSignal.BOOKING_SURGE) == 0


def test_the_16th_cancellation_an_hour_fires_the_alert(world: BookingWorld) -> None:
    business_id = BusinessId()
    cancelled = [world.booking(business_id, BookingStatus.CANCELLED) for _ in range(16)]

    for booking_id in cancelled[:15]:
        world.announce(business_id, LiveEventKind.BOOKING_CHANGED, (booking_id,))
    assert CANCELLATION_SURGE_PER_HOUR == 15
    assert not world.observe(PlatformAlertCode.CANCELLATION_SPIKE).is_firing

    world.announce(business_id, LiveEventKind.BOOKING_CHANGED, (cancelled[15],))

    assert world.signals(PlatformSignal.CANCELLATION_SURGE) == 1
    assert world.observe(PlatformAlertCode.CANCELLATION_SPIKE).is_firing


@pytest.mark.parametrize(
    ("status", "age_seconds"),
    [
        # Moved or confirmed: a change, not a cancellation.
        (BookingStatus.CONFIRMED, 0),
        # Cancelled long ago: a later change of it is no new cancellation.
        (BookingStatus.CANCELLED, 5 * 60),
    ],
)
def test_other_booking_changes_are_no_cancellations(
    world: BookingWorld, status: BookingStatus, age_seconds: int
) -> None:
    business_id = BusinessId()
    booking_id = world.booking(business_id, status, age_seconds)

    world.announce(business_id, LiveEventKind.BOOKING_CHANGED, (booking_id,), 30)

    assert world.signals(PlatformSignal.CANCELLATION_SURGE) == 0


def test_a_change_without_a_booking_counts_nothing(world: BookingWorld) -> None:
    business_id = BusinessId()

    world.announce(business_id, LiveEventKind.BOOKING_CHANGED, (BookingId(),), 30)
    world.announce(business_id, LiveEventKind.BOOKING_CHANGED, (), 30)
    world.announce(business_id, LiveEventKind.LEAD_CREATED, times=60)

    assert world.signals(PlatformSignal.CANCELLATION_SURGE) == 0
    assert world.signals(PlatformSignal.BOOKING_SURGE) == 0


def test_owners_test_bookings_never_count(world: BookingWorld) -> None:
    publisher = EventPublisherFacilitator(
        InMemoryLiveEventBusAdapter(),
        world.ops.clock.wall_clock,
        observers=[world.observer],
    )
    business_id = BusinessId()

    for _ in range(60):
        publisher.publish(business_id, LiveEventKind.BOOKING_CREATED, is_sandbox=True)
    assert world.signals(PlatformSignal.BOOKING_SURGE) == 0

    for _ in range(41):
        publisher.publish(business_id, LiveEventKind.BOOKING_CREATED)
    assert world.signals(PlatformSignal.BOOKING_SURGE) == 1


def count_elsewhere(world: BookingWorld, business_id: BusinessId, times: int) -> None:
    """New bookings another process counted in the same hour's bucket."""

    window = locate_window(world.ops.clock.wall_clock.now_unix(), HOUR_WINDOW)
    counter = RateLimitCounter(
        key=RateLimitKey(f"{NEW_BOOKINGS_KEY}{business_id}"), limit=UNLIMITED
    )
    for _ in range(times):
        world.ops.buckets.count_if_within([counter], window)


def test_a_count_that_passes_the_edge_elsewhere_still_alerts_once(
    world: BookingWorld,
) -> None:
    # Concurrent processes counted the 41st and 42nd booking together: no
    # one of them read exactly 41, yet the hour alerts, and only once.
    business_id = BusinessId()
    count_elsewhere(world, business_id, int(BOOKING_SURGE_PER_HOUR) + 1)

    world.announce(business_id, LiveEventKind.BOOKING_CREATED, times=10)

    assert world.signals(PlatformSignal.BOOKING_SURGE) == 1
    assert world.observe(PlatformAlertCode.BOOKING_SPIKE).is_firing


def test_a_surge_that_goes_on_alerts_again_the_next_hour(world: BookingWorld) -> None:
    business_id = BusinessId()
    world.announce(business_id, LiveEventKind.BOOKING_CREATED, times=45)
    world.ops.clock.advance(HOUR)
    assert world.signals(PlatformSignal.BOOKING_SURGE) == 0

    world.announce(business_id, LiveEventKind.BOOKING_CREATED, times=45)

    assert world.signals(PlatformSignal.BOOKING_SURGE) == 1
    assert world.observe(PlatformAlertCode.BOOKING_SPIKE).is_firing
