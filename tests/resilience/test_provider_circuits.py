"""
The circuit breakers of the providers the platform sends through: which
provider carries a message, which failures count against its circuit, and
what the circuit tells a worker's pulse.
"""

import pytest

from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.resilience import CircuitState, OutboundProvider
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
    ProviderCircuitOpenError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
)
from app.schemas.typings.platform.constrained_integers import (
    RetryAfterSeconds,
    WorkerLaneConcurrency,
)
from app.schemas.typings.resilience.constrained_integers import (
    CircuitFailureCount,
    CircuitOpenAgeSeconds,
)
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.resilience.circuit_calls import call_through_circuit
from app.utilities.resilience.provider_circuits import (
    customer_channel_provider,
    guarded_circuits,
    provider_circuit,
    provider_slots_of_lane,
    staff_channel_provider,
)
from tests.resilience.test_circuit_breaker import Ticks

META: CircuitName = provider_circuit(OutboundProvider.META)
TELEGRAM: CircuitName = provider_circuit(OutboundProvider.TELEGRAM)


class CountingCall:
    """A provider call that raises the given error, counting its calls."""

    def __init__(self, error: BaseException | None = None) -> None:
        self.calls: int = 0
        self._error: BaseException | None = error

    def __call__(self) -> str:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return "sent"


def guarded_breaker(ticks: Ticks) -> CircuitBreakerFacilitator:
    return CircuitBreakerFacilitator(ticks.clock(), known_circuits=guarded_circuits())


def time_out(breaker: CircuitBreakerFacilitator, times: int) -> None:
    for _ in range(times):
        with pytest.raises(ExternalServiceError):
            call_through_circuit(
                breaker, META, CountingCall(ExternalServiceError("Meta timed out."))
            )


def test_each_provider_has_its_own_circuit_and_web_push_has_none() -> None:
    assert str(META) == "provider:meta"
    assert [str(circuit) for circuit in guarded_circuits()] == [
        "provider:meta",
        "provider:telegram",
        "provider:platform_bot",
        "provider:twilio_sms",
        "provider:smtp",
        "provider:flitt",
        "provider:stripe",
        "provider:elevenlabs",
    ]
    assert customer_channel_provider(ChannelKind.INSTAGRAM) is OutboundProvider.META
    assert customer_channel_provider(ChannelKind.MESSENGER) is OutboundProvider.META
    assert customer_channel_provider(ChannelKind.TELEGRAM) is OutboundProvider.TELEGRAM
    # The website chat is the platform's own: no provider to wait on.
    assert customer_channel_provider(ChannelKind.WEB_CHAT) is None
    assert (
        staff_channel_provider(ManagerContactChannel.TELEGRAM)
        is OutboundProvider.PLATFORM_BOT
    )
    assert staff_channel_provider(ManagerContactChannel.EMAIL) is OutboundProvider.SMTP
    assert (
        staff_channel_provider(ManagerContactChannel.SMS) is OutboundProvider.TWILIO_SMS
    )


@pytest.mark.parametrize(("threads", "slots"), [(1, 1), (2, 1), (4, 2), (8, 4)])
def test_a_provider_gets_half_of_the_outbound_threads(threads: int, slots: int) -> None:
    assert int(provider_slots_of_lane(WorkerLaneConcurrency(threads))) == slots


def test_the_pulse_lists_every_provider_circuit_from_the_start() -> None:
    ticks = Ticks()
    breaker = guarded_breaker(ticks)

    time_out(breaker, 2)
    snapshot = {view.circuit: view for view in breaker.snapshot()}

    assert sorted(snapshot) == sorted(guarded_circuits())
    assert snapshot[META].state is CircuitState.CLOSED
    assert snapshot[META].recent_failures == CircuitFailureCount(2)
    assert snapshot[META].open_for_seconds is None
    assert snapshot[TELEGRAM].recent_failures == CircuitFailureCount(0)
    # Failures older than the window no longer count.
    ticks.advance(61)
    [meta] = [view for view in breaker.snapshot() if view.circuit == META]
    assert meta.recent_failures == CircuitFailureCount(0)


def test_five_timeouts_open_the_circuit_and_it_refuses_without_a_call() -> None:
    ticks = Ticks()
    breaker = guarded_breaker(ticks)

    time_out(breaker, 5)
    ticks.advance(12)
    call = CountingCall()
    with pytest.raises(ProviderCircuitOpenError) as refused:
        call_through_circuit(breaker, META, call)

    assert call.calls == 0
    assert refused.value.retry_after_seconds == RetryAfterSeconds(18)
    [meta] = [view for view in breaker.snapshot() if view.circuit == META]
    assert meta.state is CircuitState.OPEN
    assert meta.open_for_seconds == CircuitOpenAgeSeconds(12)
    # Telegram is another provider: its calls go on.
    assert call_through_circuit(breaker, TELEGRAM, CountingCall()) == "sent"


def test_after_thirty_seconds_one_trial_goes_through_and_closes_the_circuit() -> None:
    ticks = Ticks()
    breaker = guarded_breaker(ticks)
    time_out(breaker, 5)

    ticks.advance(30)
    assert breaker.seconds_until_trial(META) is None
    assert breaker.allows_call(META)
    assert breaker.state(META) is CircuitState.HALF_OPEN
    # While the trial runs, other calls are refused.
    with pytest.raises(ProviderCircuitOpenError) as refused:
        call_through_circuit(breaker, META, CountingCall())
    assert refused.value.retry_after_seconds is None
    breaker.record_success(META)

    assert breaker.state(META) is CircuitState.CLOSED


def test_a_failed_trial_opens_the_circuit_for_another_thirty_seconds() -> None:
    ticks = Ticks()
    breaker = guarded_breaker(ticks)
    time_out(breaker, 5)
    ticks.advance(31)

    with pytest.raises(ExternalServiceError):
        call_through_circuit(
            breaker, META, CountingCall(ExternalServiceError("Meta returned 503."))
        )

    assert breaker.state(META) is CircuitState.OPEN
    assert breaker.seconds_until_trial(META) == RetryAfterSeconds(30)


@pytest.mark.parametrize(
    "answer",
    [
        ProviderRejectedMessageError("Meta refused the message (131026)."),
        ProviderRateLimitedError("Meta asked to slow down."),
        AuthenticationRequiredError("The channel has no access token."),
    ],
)
def test_an_answer_or_a_missing_setting_is_not_an_outage(answer: Exception) -> None:
    ticks = Ticks()
    breaker = guarded_breaker(ticks)
    time_out(breaker, 4)

    for _ in range(3):
        with pytest.raises(type(answer)):
            call_through_circuit(breaker, META, CountingCall(answer))

    assert breaker.state(META) is CircuitState.CLOSED
    [meta] = [view for view in breaker.snapshot() if view.circuit == META]
    assert meta.recent_failures == CircuitFailureCount(0)


def test_an_unreadable_answer_counts_so_a_trial_never_stays_unreported() -> None:
    ticks = Ticks()
    breaker = guarded_breaker(ticks)
    time_out(breaker, 5)
    ticks.advance(30)

    with pytest.raises(KeyError):
        call_through_circuit(breaker, META, CountingCall(KeyError("messages")))

    assert breaker.state(META) is CircuitState.OPEN
