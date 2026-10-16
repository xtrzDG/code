"""Short builders for the scripted language model's turns."""

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.llm_scripts import ScriptedLlmTurn, ScriptedToolCall
from app.schemas.typings.conversations.strings import LlmToolInputJson, MessageText


def scripted(*turns: ScriptedLlmTurn) -> ScriptedLlmAdapter:
    return ScriptedLlmAdapter.from_turns(list(turns))


def say(text: str) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(text=MessageText(text))


def call_tool(
    tool_name: AssistantToolName,
    input_json: str,
    text: str | None = None,
) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(
        text=None if text is None else MessageText(text),
        tool_calls=[
            ScriptedToolCall(
                tool_name=tool_name, input_json=LlmToolInputJson(input_json)
            )
        ],
    )
