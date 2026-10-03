"""Reading and writing scripted language model turns for the workshop's model."""

import json
from typing import cast

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn, ScriptedToolCall
from app.schemas.typings.conversations.strings import LlmToolInputJson, MessageText
from tests.e2e.harness_settings import JsonObject


def call_tool(tool_name: AssistantToolName, arguments: JsonObject) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(
        tool_calls=[
            ScriptedToolCall(
                tool_name=tool_name,
                input_json=LlmToolInputJson(json.dumps(arguments, ensure_ascii=False)),
            )
        ]
    )


def say(text: str) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(text=MessageText(text))


def read_turn(payload: str) -> JsonObject:
    return cast(JsonObject, json.loads(payload))


def read_turn_texts(payload: str) -> str:
    content: list[JsonObject] = read_turn(payload)["content"]
    return "\n".join(str(block.get("text", "")) for block in content)


def last_tool_call(request: LlmRequest) -> tuple[str, JsonObject] | None:
    """Name and parsed result of the tool answered in the last turn, if any."""

    last_turn: JsonObject = read_turn(request.transcript[-1])
    results: list[JsonObject] = [
        block for block in last_turn["content"] if block.get("type") == "tool_result"
    ]
    if not results:
        return None

    assistant_turn: JsonObject = read_turn(request.transcript[-2])
    calls: list[JsonObject] = [
        block for block in assistant_turn["content"] if block.get("type") == "tool_use"
    ]
    return str(calls[-1]["name"]), cast(JsonObject, json.loads(results[-1]["content"]))


def last_customer_text(request: LlmRequest) -> str:
    """Text of the latest turn the customer wrote (not a tool result)."""

    for payload in reversed(request.transcript):
        turn: JsonObject = read_turn(payload)
        if turn["role"] != "user":
            continue

        texts: list[str] = [
            str(block["text"])
            for block in turn["content"]
            if block.get("type") == "text"
        ]
        if texts:
            return "\n".join(texts)

    return ""
