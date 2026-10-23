"""voice_health: the voice platform's API fails, or its finished calls stop."""

import json

import pytest
from typed_time_provider import Microseconds

from app.adapters.voice.guarded_elevenlabs_client import GuardedElevenLabsClient
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.constants.monitoring import (
    PlatformAlertCode,
    PlatformAlertStatus,
    PlatformSignal,
)
from app.schemas.constants.resilience import OutboundProvider
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.platform_alerts import AlertObservation
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from app.utilities.deliveries.delivery_keys import derive_inbound_event_id
from app.utilities.resilience.provider_circuits import provider_circuit
from tests.platform_ops.elevenlabs_fakes import ScriptedElevenLabsClient
from tests.platform_ops.ops_documents import DAY, HOUR, MINUTE, NOW
from tests.platform_ops.ops_world import OpsWorld, put
from tests.resilience.test_circuit_breaker import Ticks

SHOP: BusinessId = BusinessId()
CODE: PlatformAlertCode = PlatformAlertCode.VOICE_HEALTH


def observe(world: OpsWorld) -> AlertObservation:
    [observation] = world.checks().run(
        {CODE: PLATFORM_ALERT_RULES[CODE]}, world.clock.wall_clock.now_unix()
    )
    return observation


def report(world: OpsWorld, minutes_ago: int, days_ago: int = 0) -> None:
    """A finished-call report the inbox accepted then."""

    created: int = world.clock.now - days_ago * DAY - minutes_ago * MINUTE
    provider_message_id = ProviderMessageId(f"conv-{days_ago}-{minutes_ago}")
    put(
        world.inbound_events,
        InboundEventDocument(
            id=derive_inbound_event_id(SHOP, ChannelKind.PHONE, provider_message_id),
            business_id=SHOP,
            kind=InboundEventKind.VOICE_POST_CALL,
            channel=ChannelKind.PHONE,
            provider_message_id=provider_message_id,
            created_at=Microseconds(created),
            updated_at=Microseconds(created),
        ),
    )


def busy_week(world: OpsWorld, per_day: int = 3) -> None:
    """Each of the 7 days before had `per_day` calls in these hours."""

    for day in range(1, 8):
        for index in range(per_day):
            report(world, minutes_ago=30 + 40 * index, days_ago=day)


def test_failing_api_calls_fire_the_alert_once() -> None:
    world = OpsWorld()
    for _ in range(5):
        world.signals.count(PlatformSignal.VOICE_API_CALL)
    for _ in range(3):
        world.signals.count(PlatformSignal.VOICE_API_ERROR)
    alerts = world.alerts_use_case()
    tick = JobTick(job_name=JobName("platform_alerts"), scheduled_at=NOW)

    first = alerts.run(tick)
    world.clock.advance(5 * MINUTE)
    again = alerts.run(tick)

    [state] = world.alert_state_repo.get_many([CODE])
    assert state.status is PlatformAlertStatus.FIRING
    assert "3 of 5 voice platform API calls failed" in str(state.detail)
    # One message per recipient (the team's chat and e-mail), once.
    assert int(first.processed_count) == 2
    assert int(again.processed_count) == 0
    assert [
        str(json.loads(str(queued.payload))["text"]).splitlines()[0]
        for queued in world.queue.jobs
    ] == ["[SEV2] FIRING: Phone assistant fails"] * 2


def test_two_failed_api_calls_are_within_the_threshold() -> None:
    world = OpsWorld()
    for _ in range(2):
        world.signals.count(PlatformSignal.VOICE_API_ERROR)
        world.signals.count(PlatformSignal.VOICE_API_CALL)

    assert observe(world).is_firing is False


def test_reports_that_stop_while_every_day_before_had_calls_fire() -> None:
    world = OpsWorld()
    busy_week(world)

    observation = observe(world)

    assert observation.is_firing is True
    assert "0 finished-call reports arrived in the last 3 hours" in str(
        observation.detail
    )
    assert "had at least 3 in these hours" in str(observation.detail)


def test_a_call_in_the_last_hours_keeps_it_quiet() -> None:
    world = OpsWorld()
    busy_week(world)
    report(world, minutes_ago=170)

    assert observe(world).is_firing is False


def test_one_quiet_day_in_the_week_means_no_pattern() -> None:
    world = OpsWorld()
    busy_week(world)
    for event in world.inbound_events.list_all():
        if int(event.created_at) < world.clock.now - 7 * DAY + 4 * HOUR:
            world.inbound_events.delete(str(event.id))

    assert observe(world).is_firing is False


def test_older_reports_are_outside_the_hours_compared() -> None:
    world = OpsWorld()
    for day in range(1, 8):
        for index in range(3):
            # Same days, but five hours earlier than now.
            report(world, minutes_ago=5 * 60 + index, days_ago=day)

    assert observe(world).is_firing is False


class TestCountingClient:
    def test_calls_and_provider_failures_are_counted(self) -> None:
        world = OpsWorld()
        inner = ScriptedElevenLabsClient(
            [None, ExternalServiceError("503"), NotFoundError("gone")]
        )
        client = GuardedElevenLabsClient(
            inner,
            world.signals,
            CircuitBreakerFacilitator(Ticks().clock()),
            provider_circuit(OutboundProvider.ELEVENLABS),
        )

        client.delete_conversation(ProviderCallId("conv_1"))
        with pytest.raises(ExternalServiceError):
            client.delete_conversation(ProviderCallId("conv_2"))
        with pytest.raises(NotFoundError):
            client.delete_conversation(ProviderCallId("conv_3"))

        now = world.clock.wall_clock.now_unix()
        assert int(world.signals.read(PlatformSignal.VOICE_API_CALL, now).current) == 3
        # A refusal that is not the platform's failure is not an outage.
        assert int(world.signals.read(PlatformSignal.VOICE_API_ERROR, now).current) == 1
