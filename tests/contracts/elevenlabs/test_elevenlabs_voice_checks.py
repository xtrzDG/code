"""
The voice checks against ElevenLabs agent testing's own types: the agent of
the checks, each simulated call and its run are bodies the SDK defines (every
object closed), and a finished run as the platform answers it is read into
the outcome the autotests judge.
"""

from typing import Any

from app.adapters.voice.elevenlabs_voice_check_bodies import read_test_run
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.voice_checks import VoiceCheckStatus
from tests.channels.voice_check_setup import (
    batch,
    build_voice_check_setup,
    case,
    finished_invocation,
)
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.elevenlabs.elevenlabs_cases import AGENTS_SPEC
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound


def test_a_finished_run_matches_the_sdk_type() -> None:
    assert_inbound(
        load_json_fixture("elevenlabs", "test_invocation_finished.json"),
        AGENTS_SPEC,
        "TestInvocation",
    )


def test_the_bodies_of_the_checks_match_the_sdk_types() -> None:
    setup = build_voice_check_setup()
    transport = setup.transport
    transport.respond("POST", r"^/v1/convai/agent-testing/create$", {"id": "test_ka"})
    transport.respond("POST", r"/run-tests$", {"id": "suite_ka", "test_runs": []})
    transport.respond(
        "GET", r"/test-invocations/suite_ka$", finished_invocation("test_ka")
    )

    setup.adapter.run_checks(batch("ka"))

    [agent] = transport.requests_to("/agents/create")
    assert_outbound(agent.json(), AGENTS_SPEC, "request:agents.create")
    [test] = transport.requests_to("/agent-testing/create")
    assert_outbound(test.json(), AGENTS_SPEC, "request:agent_testing.create")
    [run] = transport.requests_to("/run-tests")
    assert_outbound(run.json(), AGENTS_SPEC, "request:agents.run_tests")


def test_a_finished_run_is_read() -> None:
    invocation: dict[str, Any] = load_json_fixture(
        "elevenlabs", "test_invocation_finished.json"
    )
    [run] = invocation["test_runs"]

    outcome = read_test_run(case("ka"), run)

    assert outcome.status is VoiceCheckStatus.PASSED
    assert [line.author for line in outcome.lines] == [
        MessageAuthor.ASSISTANT,
        MessageAuthor.CUSTOMER,
        MessageAuthor.ASSISTANT,
    ]
    [tool_call] = outcome.tool_calls
    assert tool_call.tool_name is AssistantToolName.CREATE_BOOKING
    assert '"party_size": 2' in str(tool_call.input_json)
    assert [str(reason) for reason in outcome.rationale] == [
        "The agent booked two people for 19:00 tomorrow and read it back.",
        "The greeting says it is an AI assistant.",
    ]
    # llm_price + platform_price, in USD.
    assert int(outcome.cost_micro_usd) == 16_000
