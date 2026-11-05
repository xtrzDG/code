"""
The ElevenLabs voice check adapter over a recording transport, a clock the
polls move instead of sleeping, and the cases and runs the tests script.
"""

import copy
from dataclasses import dataclass
from typing import Any

from app.adapters.voice.elevenlabs_voice_check_adapter import (
    ElevenLabsVoiceCheckAdapter,
)
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.voice_checks import (
    VoiceCheckBatch,
    VoiceCheckCallContext,
    VoiceCheckCase,
    VoiceToolMock,
)
from app.schemas.typings.assistants.constrained_strings import AutotestScenarioKey
from app.schemas.typings.channels.strings import CallLocalTimeText, CallNextDaysText
from app.schemas.typings.conversations.strings import LlmToolResultJson
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.voice.constrained_integers import VoiceCheckWaitSeconds
from app.schemas.typings.voice.strings import VoiceCheckBrief, VoiceCheckCondition
from tests.channels.recording_transport import RecordingTransport
from tests.channels.testbed import ChannelsTestbed
from tests.channels.voice_agent_specs import build_spec
from tests.contracts.contract_files import load_json_fixture
from tests.resilience.test_circuit_breaker import Ticks

POLL_SECONDS: float = 5.0
WAIT_SECONDS: int = 60


@dataclass
class VoiceCheckSetup:
    testbed: ChannelsTestbed
    ticks: Ticks
    adapter: ElevenLabsVoiceCheckAdapter
    sleeps: list[float]

    @property
    def transport(self) -> RecordingTransport:
        return self.testbed.elevenlabs_transport


def build_voice_check_setup() -> VoiceCheckSetup:
    """The adapter; every sleep moves the monotonic clock instead."""

    testbed = ChannelsTestbed()
    ticks = Ticks()
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        ticks.advance(seconds)

    adapter = ElevenLabsVoiceCheckAdapter(
        testbed.elevenlabs_client,
        testbed.settings,
        ticks.clock(),
        sleep=sleep,
        wait_seconds=VoiceCheckWaitSeconds(WAIT_SECONDS),
        poll_seconds=POLL_SECONDS,
    )
    transport = testbed.elevenlabs_transport
    transport.respond("POST", r"^/v1/convai/tools$", {"id": "tool_check"})
    transport.respond(
        "POST", r"^/v1/convai/agents/create$", {"agent_id": "agent_check"}
    )
    transport.respond("DELETE", r"^/v1/convai/", {})
    return VoiceCheckSetup(testbed, ticks, adapter, sleeps)


def case(language: str) -> VoiceCheckCase:
    return VoiceCheckCase(
        key=AutotestScenarioKey(f"phone__booking__{language}"),
        language=LanguageTag(language),
        brief=VoiceCheckBrief(f"Book a table in {language}."),
        condition=VoiceCheckCondition("The booking was made and read back."),
        call_context=VoiceCheckCallContext(
            local_now_text=CallLocalTimeText("Thursday 2026-10-01 14:05"),
            next_days_text=CallNextDaysText("Fri 2026-10-02, Sat 2026-10-03"),
            timezone=TimezoneName("Asia/Tbilisi"),
        ),
        tool_mocks=[
            VoiceToolMock(
                tool_name=AssistantToolName.CREATE_BOOKING,
                result_json=LlmToolResultJson('{"status": "confirmed"}'),
            )
        ],
    )


def batch(*languages: str) -> VoiceCheckBatch:
    return VoiceCheckBatch(
        agent=build_spec(), cases=[case(language) for language in languages]
    )


def finished_invocation(
    test_id: str, status: str = "passed", party_size: int = 2
) -> dict[str, Any]:
    """The contract fixture's finished run, for `test_id`."""

    invocation: dict[str, Any] = copy.deepcopy(
        load_json_fixture("elevenlabs", "test_invocation_finished.json")
    )
    [run] = invocation["test_runs"]
    run["test_id"] = test_id
    run["status"] = status
    tool_call: dict[str, Any] = run["agent_responses"][2]["tool_calls"][0]
    tool_call["params_as_json"] = (
        '{"arguments": {"party_size": ' + str(party_size) + "}}"
    )
    return invocation


def pending_invocation(test_id: str) -> dict[str, Any]:
    invocation = finished_invocation(test_id)
    invocation["test_runs"][0]["status"] = "pending"
    return invocation
