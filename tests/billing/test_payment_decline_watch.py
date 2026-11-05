"""
Declined payments per business (LOG-05, card testing): the 5th decline
within two hours counts the platform signal of the `tenant_payment_declines`
alert, the 10th counts it again and brakes the business's new payment
pages (checkout and "Save card" answer 429) until the hourly windows cool
down. Retries of a declined automatic charge never count, and one
business's declines never brake another.
"""

from collections.abc import Sequence

import pytest
from typed_time_provider import Microseconds, WallClock

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.facilitators.billing.payment_decline_watch_facilitator import (
    ALERT_DECLINES,
    BRAKE_DECLINES,
    PaymentDeclineWatchFacilitator,
)
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.dto.payment_methods import StartCardSetupCommand, StartCardSetupRequest
from app.schemas.dto.rate_limits import RateLimitCounter, RateLimitWindow
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.billing.constrained_integers import PaymentRetryAttempt
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.billing.payment_retry_identity import derive_payment_retry_id
from tests.billing.paid_world import PaidWorld, build_trial, checkout, payment_order
from tests.platform_ops.failure_signal_doubles import CountedSignals

HOUR: int = 3_600_000_000
START: int = 1_790_000_000_000_000


class BrokenBuckets(InMemoryRateLimitBucketAdapter):
    def count_if_within(
        self, counters: Sequence[RateLimitCounter], window: RateLimitWindow
    ) -> RateLimitKey | None:
        del counters, window
        raise RuntimeError("database down")


class DeclineWorld:
    def __init__(self) -> None:
        self.now: int = START
        self.signals = CountedSignals()
        self.watch = PaymentDeclineWatchFacilitator(
            buckets=InMemoryRateLimitBucketAdapter(),
            signal_counter=self.signals,
            wall_clock=WallClock(
                preferred_time_unit_type=Microseconds,
                unix_nanosecond_factory=lambda: self.now * 1_000,
            ),
        )

    def decline(self, business_id: BusinessId, times: int) -> None:
        for _ in range(times):
            self.watch.record_decline(business_id)

    def alerts(self) -> int:
        return self.signals.of(PlatformSignal.TENANT_PAYMENT_DECLINES)


def test_the_fifth_decline_alerts_and_the_tenth_brakes_the_payment_pages() -> None:
    world = DeclineWorld()
    business, other = BusinessId(), BusinessId()

    world.decline(business, ALERT_DECLINES - 1)
    assert world.alerts() == 0
    world.decline(business, 1)
    assert world.alerts() == 1
    world.decline(business, BRAKE_DECLINES - ALERT_DECLINES - 1)
    world.watch.require_payment_pages(business)
    assert world.alerts() == 1

    world.decline(business, 1)

    assert world.alerts() == 2
    with pytest.raises(RateLimitedError) as refused:
        world.watch.require_payment_pages(business)
    assert refused.value.retry_after_seconds is not None
    assert int(refused.value.retry_after_seconds) == 3600
    world.watch.require_payment_pages(other)


def test_the_brake_lifts_once_two_hours_are_quiet() -> None:
    world = DeclineWorld()
    business = BusinessId()
    world.decline(business, BRAKE_DECLINES)

    world.now += HOUR
    with pytest.raises(RateLimitedError):
        world.watch.require_payment_pages(business)

    world.now += HOUR
    world.watch.require_payment_pages(business)


def test_a_count_that_cannot_be_written_never_fails_the_payment() -> None:
    signals = CountedSignals()
    watch = PaymentDeclineWatchFacilitator(
        buckets=BrokenBuckets(),
        signal_counter=signals,
        wall_clock=WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: START * 1_000,
        ),
    )

    watch.record_decline(BusinessId())

    assert signals.calls == []


def declined(world: PaidWorld, payment_id: int, is_retry: bool = False) -> None:
    order = payment_order(world, checkout(world))
    parameters = world.testbed.callback_parameters(
        order,
        "declined",
        payment_id=payment_id,
        response_description="Declined by issuer",
    )
    if is_retry:
        parameters["order_id"] = str(
            derive_payment_retry_id(InvoiceId(), PaymentRetryAttempt(1))
        )
    world.testbed.deliver_flitt_callback(parameters)


def save_card(world: PaidWorld) -> None:
    world.testbed.payments.start_card_setup.run(
        StartCardSetupCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=StartCardSetupRequest(),
        )
    )


def test_declined_checkouts_brake_new_payment_pages_of_that_business() -> None:
    world = build_trial()
    signals = world.testbed.payments.decline_signals

    for payment_id in range(1, BRAKE_DECLINES + 1):
        declined(world, payment_id)

    assert signals.of(PlatformSignal.TENANT_PAYMENT_DECLINES) == 2
    with pytest.raises(RateLimitedError):
        checkout(world)
    with pytest.raises(RateLimitedError):
        save_card(world)


def test_declined_retries_of_automatic_charges_never_count() -> None:
    world = build_trial()

    for payment_id in range(1, BRAKE_DECLINES + 1):
        declined(world, payment_id, is_retry=True)

    assert world.testbed.payments.decline_signals.calls == []
    checkout(world)
