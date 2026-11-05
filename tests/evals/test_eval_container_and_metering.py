"""The evaluation container's settings, clock and model seam; call metering."""

import pytest

from app.adapters.llm.llm_payloads import (
    build_tool_results_payload,
    build_user_text_payload,
)
from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.typings.assistants.constrained_integers import (
    LlmPricePerMillionTokensMicroUsd as Price,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_integers import ElapsedMilliseconds
from app.utilities.assembly.autotest_prompts import (
    CUSTOMER_PERSONA_OPENING,
    JUDGE_SYSTEM_PROMPT,
    build_customer_persona_prompt,
)
from scripts.eval_harness.call_metering import CallMeter, CallRole, role_of
from scripts.eval_harness.eval_container import (
    SteppingClock,
    SwitchableLlmAdapter,
    build_environment,
)
from tests.evals.eval_builders import llm_request, llm_response, scenario, user_turn


def test_the_environment_takes_the_model_and_only_provider_keys() -> None:
    environment = build_environment(
        LlmModelId("gpt-5-mini"),
        {"OPENAI_API_KEY": "test-key-0000", "ANTHROPIC_API_KEY": "", "HOME": "/root"},
    )

    assert environment["LLM_PROVIDER"] == "openai"
    assert environment["LLM_MODEL_ID"] == "gpt-5-mini"
    assert environment["OPENAI_API_KEY"] == "test-key-0000"
    assert "ANTHROPIC_API_KEY" not in environment
    assert "HOME" not in environment
    assert build_environment(LlmModelId("scripted"), {})["LLM_PROVIDER"] == "scripted"


def test_the_clock_ticks_and_resets() -> None:
    clock = SteppingClock()
    first = clock()

    assert clock() == first + 1_000_000
    clock.reset()
    assert clock() == first


def test_the_seam_needs_an_adapter_and_follows_it() -> None:
    seam = SwitchableLlmAdapter()
    with pytest.raises(RuntimeError, match="No language model"):
        seam.complete(llm_request([user_turn("Hi")]))

    seam.use(ScriptedLlmAdapter(lambda _: ScriptedLlmTurn(text=MessageText("Hello"))))

    assert seam.complete(llm_request([user_turn("Hi")])).text == "Hello"
    assert seam.build_user_text_turn(MessageText("Hi")) == build_user_text_payload(
        MessageText("Hi")
    )
    assert seam.build_tool_results_turn([]) == build_tool_results_payload([])


def test_the_meter_adds_cost_by_role_and_assistant_time() -> None:
    meter = CallMeter(
        [
            LlmTokenPrice(
                model_id=LlmModelId("gpt-5-mini"),
                input_price=Price(1_000_000),
                output_price=Price(2_000_000),
            )
        ]
    )
    answer = llm_response("Hi").model_copy(
        update={"input_tokens": LlmTokenCount(10), "output_tokens": LlmTokenCount(5)}
    )
    meter.observe(
        llm_request([user_turn("Hi")], model="gpt-5-mini"),
        answer,
        ElapsedMilliseconds(30),
    )
    meter.observe(
        llm_request([user_turn("Hi")], JUDGE_SYSTEM_PROMPT, "gpt-5-mini"),
        answer,
        ElapsedMilliseconds(99),
    )

    assert meter.total_cost_micro_usd == 40
    assert meter.cost_micro_usd[CallRole.JUDGE] == 20
    assert meter.assistant_elapsed_ms == 30
    assert (
        role_of(llm_request([], f"{CUSTOMER_PERSONA_OPENING} x")) is CallRole.CUSTOMER
    )


def test_a_persona_can_bring_its_own_name() -> None:
    with_name = build_customer_persona_prompt(
        "Hotel", scenario("en"), None, [], ContactName("Emma")
    )
    without_name = build_customer_persona_prompt("Hotel", scenario("en"), None, [])

    assert "Your name is Emma; give it when the assistant asks." in with_name
    assert "give a first name that is common among speakers of English" in without_name
