"""The conversation engine over the real provider adapters and SDKs (mock HTTP)."""

import json
from typing import Any

from app.adapters.llm.anthropic_llm_adapter import AnthropicLlmAdapter
from app.adapters.llm.openai_llm_adapter import OpenAiLlmAdapter
from app.adapters.llm.routing_llm_adapter import RoutingLlmAdapter
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.conversations import ReplyGuardVerdict
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.provider_http_fakes import (
    ScriptedHttp,
    anthropic_message,
    build_anthropic_client,
    build_openai_client,
    openai_function_call_item,
    openai_message_item,
    openai_reasoning_item,
    openai_response,
)

PRICE_ARGUMENTS: dict[str, str] = {"item_name": "khachapuri"}


def routed_world(openai_http: ScriptedHttp, anthropic_http: ScriptedHttp) -> BrainWorld:
    return build_world(
        RoutingLlmAdapter(
            openai_adapter=OpenAiLlmAdapter(build_openai_client(openai_http)),
            anthropic_adapter=AnthropicLlmAdapter(
                build_anthropic_client(anthropic_http)
            ),
        )
    )


def use_model(world: BrainWorld, model_id: str) -> None:
    world.version.model_id = LlmModelId(model_id)
    world.version_repo.save(world.version)


def test_openai_turns_are_replayed_by_the_engine_across_messages() -> None:
    openai_http = ScriptedHttp(
        [
            openai_response(
                [
                    openai_reasoning_item("rs_1"),
                    openai_function_call_item("get_price", PRICE_ARGUMENTS, "call_1"),
                ],
                input_tokens=2_000,
                output_tokens=100,
            ),
            openai_response(
                [openai_reasoning_item("rs_2"), openai_message_item("18 GEL.")],
                input_tokens=2_200,
                output_tokens=50,
            ),
            openai_response([openai_message_item("You are welcome!")]),
        ]
    )
    world = routed_world(openai_http, ScriptedHttp([]))
    use_model(world, "gpt-5-mini")

    first = world.send("How much is khachapuri?")
    second = world.send("Thanks!")

    assert first.guard_verdict is ReplyGuardVerdict.CLEAN
    assert first.text is not None
    assert first.text.endswith("18 GEL.")
    assert second.text == "You are welcome!"
    third_input: list[dict[str, Any]] = openai_http.body(2)["input"]
    assert [item.get("type", item.get("role")) for item in third_input] == [
        "user",
        "reasoning",
        "function_call",
        "function_call_output",
        "reasoning",
        "message",
        "user",
    ]
    assert third_input[1]["encrypted_content"] == "gAAAA-encrypted-rs_1"
    tool_output = json.loads(third_input[3]["output"])
    assert tool_output["matches"][0]["price"] == "18.00"
    assert "[Customer message]\nThanks!" in third_input[6]["content"][0]["text"]
    outbound = world.messages(first.conversation_id)[1]
    assert int(outbound.input_tokens) == 4_200
    assert int(outbound.cost_micro_usd) == 1_050 + 300
    assert {event.kind for event in world.usage_events()} == {
        UsageKind.LLM_INPUT_TOKENS,
        UsageKind.LLM_OUTPUT_TOKENS,
        UsageKind.DIALOG,
    }


def test_anthropic_turns_are_replayed_by_the_engine() -> None:
    anthropic_http = ScriptedHttp(
        [
            anthropic_message(
                [
                    {"type": "thinking", "thinking": "", "signature": "s1"},
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "get_price",
                        "input": PRICE_ARGUMENTS,
                    },
                ],
                "tool_use",
            ),
            anthropic_message(
                [{"type": "text", "text": "Хачапури — 18 лари."}], "end_turn"
            ),
        ]
    )
    world = routed_world(ScriptedHttp([]), anthropic_http)
    use_model(world, "claude-opus-5-5")

    reply = world.send("Сколько стоит хачапури?")

    assert reply.text is not None
    assert reply.text.endswith("Хачапури — 18 лари.")
    messages: list[dict[str, Any]] = anthropic_http.body(1)["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant", "user"]
    assert messages[1]["content"][0] == {
        "type": "thinking",
        "thinking": "",
        "signature": "s1",
    }
    assert messages[2]["content"][0]["tool_use_id"] == "toolu_1"
    outbound = world.messages(reply.conversation_id)[1]
    assert int(outbound.input_tokens) == 2_000
    assert int(outbound.cost_micro_usd) == 2_000 * 4 + 80 * 20
