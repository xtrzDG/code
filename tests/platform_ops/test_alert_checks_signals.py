"""
The alert checks that read the shared signal counters (model calls and
failures, refused login codes) and the activity of the last hour and week
(handoffs, failed tool calls), with the counters' producers.
"""

from collections.abc import Sequence

import pytest

from app.adapters.llm.offline_llm_adapter import OfflineLlmAdapter
from app.adapters.llm.signal_counting_llm_adapter import SignalCountingLlmAdapter
from app.facilitators.users.login_code_cap_alert_facilitator import (
    LoginCodeCapAlertFacilitator,
)
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.monitoring import PlatformAlertCode, PlatformSignal
from app.schemas.constants.users import LoginCodeCap
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.dto.login_protection import LoginCodeCapAlert
from app.schemas.dto.platform_alerts import AlertObservation
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    LlmRefusedError,
)
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.users.constrained_integers import OtpSendLimit
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from tests.platform_ops.ops_documents import DAY, HOUR, MINUTE, NOW, at, handoff, reply
from tests.platform_ops.ops_world import OpsWorld, put

SHOP: BusinessId = BusinessId()


def observe(world: OpsWorld, code: PlatformAlertCode) -> AlertObservation:
    [observation] = world.checks().run(
        {code: PLATFORM_ALERT_RULES[code]}, world.clock.wall_clock.now_unix()
    )
    return observation


def count(world: OpsWorld, signal: PlatformSignal, times: int) -> None:
    for _ in range(times):
        world.signals.count(signal)


class FailingModel(OfflineLlmAdapter):
    """The offline model whose calls fail with the given errors, in turn."""

    def __init__(self, errors: Sequence[Exception | None]) -> None:
        super().__init__()
        self._errors: list[Exception | None] = list(errors)

    def complete(self, request: LlmRequest) -> LlmResponse:
        error = self._errors.pop(0)
        if error is not None:
            raise error
        return super().complete(request)


def model_request() -> LlmRequest:
    return LlmRequest(
        model_id=LlmModelId("scripted"),
        system_prompt=SystemPromptText("You are the assistant of a bakery."),
        tools=[],
        transcript=[OfflineLlmAdapter().build_user_text_turn(MessageText("Hi"))],
        max_output_tokens=LlmMaxOutputTokens(100),
        effort=LlmEffort.LOW,
    )


def test_model_failures_are_counted_but_refusals_are_answers() -> None:
    world = OpsWorld()
    model = SignalCountingLlmAdapter(
        FailingModel([None, ExternalServiceError("overloaded"), LlmRefusedError("no")]),
        world.signals,
    )

    model.complete(model_request())
    for error_type in (ExternalServiceError, LlmRefusedError):
        with pytest.raises(error_type):
            model.complete(model_request())

    now = world.clock.wall_clock.now_unix()
    assert int(world.signals.read(PlatformSignal.LLM_CALL, now).current) == 3
    assert int(world.signals.read(PlatformSignal.LLM_ERROR, now).current) == 1


def test_model_errors_fire_above_five_percent_of_twenty_calls() -> None:
    quiet, firing, too_few = OpsWorld(), OpsWorld(), OpsWorld()
    for world, calls, errors in ((quiet, 40, 2), (firing, 40, 3), (too_few, 10, 9)):
        count(world, PlatformSignal.LLM_CALL, calls)
        count(world, PlatformSignal.LLM_ERROR, errors)

    assert not observe(quiet, PlatformAlertCode.LLM_ERRORS).is_firing
    observation = observe(firing, PlatformAlertCode.LLM_ERRORS)
    assert observation.is_firing and int(observation.figure) == 8
    assert not observe(too_few, PlatformAlertCode.LLM_ERRORS).is_firing


def test_signals_of_the_window_before_count_and_older_ones_do_not() -> None:
    world = OpsWorld()
    count(world, PlatformSignal.OTP_CAP_TRIP, 1)
    world.clock.advance(20 * MINUTE)
    still = observe(world, PlatformAlertCode.OTP_CAP_TRIPS)
    world.clock.advance(30 * MINUTE)

    gone = observe(world, PlatformAlertCode.OTP_CAP_TRIPS)

    assert still.is_firing and int(still.figure) == 1
    assert not gone.is_firing


def test_every_refused_login_code_is_counted() -> None:
    world = OpsWorld()
    alerts = LoginCodeCapAlertFacilitator(
        None, [], world.clock.wall_clock, signal_counter=world.signals
    )
    alert = LoginCodeCapAlert(cap=LoginCodeCap.NEW_DESTINATIONS, limit=OtpSendLimit(50))

    for _ in range(3):
        alerts.report_cap_reached(alert)

    observation = observe(world, PlatformAlertCode.OTP_CAP_TRIPS)
    assert observation.is_firing and int(observation.figure) == 3


def test_handoffs_spike_above_three_times_the_weekly_hourly_mean() -> None:
    usual, spike, sandbox = OpsWorld(), OpsWorld(), OpsWorld()
    week = [handoff(SHOP, at(-HOUR - index * HOUR - 1)) for index in range(168)]
    for world in (usual, spike, sandbox):
        put(world.handoffs, *week)
    put(usual.handoffs, *(handoff(SHOP, at(-index * MINUTE - 1)) for index in range(3)))
    put(spike.handoffs, *(handoff(SHOP, at(-index * MINUTE - 1)) for index in range(6)))
    put(
        sandbox.handoffs,
        *(
            handoff(SHOP, at(-index * MINUTE - 1), is_sandbox=True)
            for index in range(9)
        ),
    )

    assert not observe(usual, PlatformAlertCode.HANDOFF_SPIKE).is_firing
    observation = observe(spike, PlatformAlertCode.HANDOFF_SPIKE)
    assert observation.is_firing and int(observation.figure) == 6
    assert "the week before averaged 1.0 an hour" in str(observation.detail)
    assert not observe(sandbox, PlatformAlertCode.HANDOFF_SPIKE).is_firing


def test_a_new_platform_needs_five_handoffs_for_a_spike() -> None:
    world = OpsWorld()
    put(world.handoffs, *(handoff(SHOP, at(-index * MINUTE - 1)) for index in range(4)))

    assert not observe(world, PlatformAlertCode.HANDOFF_SPIKE).is_firing
    put(world.handoffs, handoff(SHOP, at(-30 * MINUTE)))
    assert observe(world, PlatformAlertCode.HANDOFF_SPIKE).is_firing


def test_tool_errors_fire_above_five_replies_an_hour() -> None:
    world = OpsWorld()
    put(world.messages, *(reply(SHOP, at(-index - 1), True) for index in range(5)))
    put(world.messages, reply(SHOP, at(-MINUTE), False))
    put(world.messages, reply(SHOP, at(-DAY), True))
    five = observe(world, PlatformAlertCode.TOOL_ERRORS)
    put(world.messages, reply(SHOP, at(-2 * MINUTE), True))

    six = observe(world, PlatformAlertCode.TOOL_ERRORS)

    assert not five.is_firing and int(five.figure) == 5
    assert six.is_firing and int(six.figure) == 6
    assert int(NOW) == int(world.clock.wall_clock.now_unix())
