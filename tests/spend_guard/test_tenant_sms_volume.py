"""
A business's SMS volume (LOG-05): the 61st SMS of an hour counts the
`tenant_sms_volume` signal once, from the 200th the business's SMS are
refused until the next hour, and SMS outside a business pass unchanged.
"""

import pytest
from typed_time_provider import Microseconds, WallClock

from app.adapters.notifications.tenant_sms_volume_guard_adapter import (
    ALERT_VOLUME,
    CAP_VOLUME,
    TenantSmsVolumeGuardAdapter,
)
from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.containers.adapters.provider_guards import guard_tenant_sms_volume
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.exceptions.application_errors import ProviderRateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.strings import SmsMessageText
from app.utilities.observability.log_context import bound_log_context
from tests.platform_ops.failure_signal_doubles import CountedSignals

HOUR_MICROSECONDS: int = 3_600_000_000
START: int = 1_790_000_000_000_000
RECIPIENT: E164PhoneNumber = E164PhoneNumber("+393331234567")
TEXT: SmsMessageText = SmsMessageText("Your table is booked for 20:00.")


class SentSms:
    """The SMS the provider was asked to send."""

    def __init__(self) -> None:
        self.recipients: list[E164PhoneNumber] = []

    def send_sms(self, recipient: E164PhoneNumber, text: SmsMessageText) -> None:
        del text
        self.recipients.append(recipient)


class SmsWorld:
    """The guard over a recording provider, in-memory buckets and a clock."""

    def __init__(self) -> None:
        self.now: int = START
        self.sent = SentSms()
        self.signals = CountedSignals()
        self.guard = TenantSmsVolumeGuardAdapter(
            self.sent,
            InMemoryRateLimitBucketAdapter(),
            self.signals,
            WallClock(
                preferred_time_unit_type=Microseconds,
                unix_nanosecond_factory=lambda: self.now * 1_000,
            ),
        )

    def send_for(self, business_id: BusinessId | None, times: int) -> None:
        with bound_log_context(business_id=business_id):
            for _ in range(times):
                self.guard.send_sms(RECIPIENT, TEXT)

    def surges(self) -> int:
        return self.signals.of(PlatformSignal.TENANT_SMS_SURGE)


def test_an_hour_up_to_the_alert_volume_is_quiet() -> None:
    world = SmsWorld()

    world.send_for(BusinessId(), ALERT_VOLUME)

    assert len(world.sent.recipients) == ALERT_VOLUME
    assert world.surges() == 0


def test_the_sms_past_the_alert_volume_counts_one_surge() -> None:
    world = SmsWorld()

    world.send_for(BusinessId(), ALERT_VOLUME + 20)

    assert len(world.sent.recipients) == ALERT_VOLUME + 20
    assert world.surges() == 1


def test_the_cap_refuses_until_the_next_hour() -> None:
    world = SmsWorld()
    business = BusinessId()
    world.send_for(business, int(CAP_VOLUME))

    with pytest.raises(ProviderRateLimitedError) as refused:
        world.send_for(business, 1)
    world.now += HOUR_MICROSECONDS
    world.send_for(business, 1)

    assert refused.value.retry_after_seconds is not None
    assert len(world.sent.recipients) == int(CAP_VOLUME) + 1
    assert world.surges() == 2


def test_each_business_has_its_own_hour() -> None:
    world = SmsWorld()
    busy = BusinessId()
    world.send_for(busy, int(CAP_VOLUME))

    world.send_for(BusinessId(), 1)

    assert len(world.sent.recipients) == int(CAP_VOLUME) + 1


def test_sms_outside_a_business_are_not_counted() -> None:
    world = SmsWorld()

    world.send_for(None, int(CAP_VOLUME) + 5)

    assert len(world.sent.recipients) == int(CAP_VOLUME) + 5
    assert world.surges() == 0


def test_no_provider_means_no_guard() -> None:
    buckets = InMemoryRateLimitBucketAdapter()
    clock = WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: START * 1_000,
    )

    assert guard_tenant_sms_volume(None, buckets, clock) is None
    assert isinstance(
        guard_tenant_sms_volume(SentSms(), buckets, clock),
        TenantSmsVolumeGuardAdapter,
    )
