"""One autotest conversation: the AI customer, the judge model, turn limits, [DONE]."""

from app.schemas.constants.assistants import (
    AutotestOutcome,
    AutotestScenarioKind,
    LlmEffort,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.dto.conversations import AssistantReply, LlmRequest
from tests.assembly.autotest_run_helpers import run_one, start
from tests.assembly.autotest_scripts import CUSTOMER_TEXTS, DONE, build_reply
from tests.assembly.llm_request_helpers import read_last_user_text
from tests.assembly.testbed import AssemblyTestbed


def test_ai_customer_and_judge_use_the_judge_model_without_tools() -> None:
    testbed = AssemblyTestbed(environment={"LLM_JUDGE_EFFORT": "high"})
    business, version = start(testbed)

    run_one(testbed, business, version, "ru", AutotestScenarioKind.HUMAN_REQUEST)

    customer_requests: list[LlmRequest] = testbed.customer_requests.requests
    judge_requests: list[LlmRequest] = testbed.judge_requests.requests
    assert len(customer_requests) == 2
    assert len(judge_requests) == 1
    for request in [*customer_requests, *judge_requests]:
        assert request.model_id == testbed.settings.llm_judge_model_id
        assert request.effort is LlmEffort.HIGH
        assert request.tools == []

    persona = str(customer_requests[0].system_prompt)
    assert "only in Russian (language tag ru)" in persona
    assert "Your goal: Ask to talk to a human employee right away." in persona
    assert "Your phone number is +995 555 12 34 56." in persona
    assert "- Opening hours on Friday: 12:00–15:00, 18:00–24:00" in persona
    assert "[DONE]" in persona
    judge_prompt = str(judge_requests[0].system_prompt)
    for criterion in (
        "facts_and_prices",
        "booking_data",
        "ai_disclosure",
        "handoff",
        "language",
    ):
        assert f"- {criterion}:" in judge_prompt

    judge_input = read_last_user_text(judge_requests[0])
    assert judge_input.startswith("Scenario: human_request__ru (human_request)\n")
    assert "- handed off to a human: yes" in judge_input
    assert "- Business name: Café Rustaveli" in judge_input
    assert f"Customer: {CUSTOMER_TEXTS['ru']}" in judge_input
    assert "Assistant: Здравствуйте! Я AI-ассистент." in judge_input


def test_ai_customer_sees_the_assistant_replies() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)

    run_one(testbed, business, version, "en", AutotestScenarioKind.UNKNOWN_QUESTION)

    second_request = testbed.customer_requests.requests[1]
    assert len(second_request.transcript) == 3
    assert read_last_user_text(second_request) == (
        "Hello! I am the AI assistant. How can I help?"
    )


def test_conversation_stops_at_the_turn_limit() -> None:
    testbed = AssemblyTestbed(environment={"AUTOTEST_TURN_LIMIT": "3"})
    business, version = start(testbed)
    testbed.customer_script = lambda request, turn: f"Message {turn + 1}"

    run = run_one(testbed, business, version, "en", AutotestScenarioKind.RUDE_CUSTOMER)

    result = run.results[0]
    assert [str(line.text) for line in result.transcript[::2]] == [
        "Message 1",
        "Message 2",
        "Message 3",
    ]
    assert len(testbed.conversation.inbound_messages) == 3
    assert len(testbed.customer_requests.requests) == 3


def test_done_marker_ends_the_conversation_without_sending_it() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.customer_script = lambda request, turn: (
        "Hello" if turn == 0 else "Thanks, bye! [DONE]"
    )

    run = run_one(testbed, business, version, "en", AutotestScenarioKind.RUDE_CUSTOMER)

    assert [str(message.text) for message in testbed.conversation.inbound_messages] == [
        "Hello"
    ]
    assert run.results[0].outcome is AutotestOutcome.PASSED


def test_customer_who_writes_nothing_errors_the_scenario() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    testbed.customer_script = lambda request, turn: DONE

    run = run_one(testbed, business, version, "en", AutotestScenarioKind.RUDE_CUSTOMER)

    result = run.results[0]
    assert result.outcome is AutotestOutcome.ERRORED
    assert result.check_notes == ["The AI customer wrote no message."]
    assert result.scores == []
    assert testbed.judge_requests.requests == []


def test_silent_reply_after_a_handoff_is_shown_to_the_customer() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)
    silent = AssistantReply.model_validate(
        build_reply("en", is_handed_off=True).model_dump() | {"text": None}
    )
    testbed.reply_scripts["human_request__en"] = lambda message, key, turn: silent

    run = run_one(testbed, business, version, "en", AutotestScenarioKind.HUMAN_REQUEST)

    result = run.results[0]
    assert result.outcome is AutotestOutcome.PASSED
    assert result.transcript[1].author is MessageAuthor.SYSTEM
    assert "did not answer" in read_last_user_text(
        testbed.customer_requests.requests[1]
    )
