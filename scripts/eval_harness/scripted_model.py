"""
The scripted model of a dataset scenario (model id "scripted"): it plays
the scenario's reference conversation. The AI customer says the
scenario's `customer` messages in order and then [DONE]; the assistant
plays the `assistant` steps in order (a step per model turn); the judge
scores every criterion 5. Each role knows how far it is from the
request's transcript alone, so the same request always gets the same
answer and the recorded cassettes are reproducible. A scenario that opens
with its message word for word (an attack, an owner check) starts the AI
customer's transcript with the continuation note: that message counts as
the customer's first. A step that `sees_photo` is the fixed answer to the
customer's photo and is played only when the request shows a picture.
"""

import json
from collections.abc import Sequence
from typing import cast

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.constants.assistants import JudgeCriterion
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn, ScriptedToolCall
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolInputJson,
    MessageText,
)
from app.utilities.assembly.autotest_prompts import (
    CUSTOMER_PERSONA_OPENING,
    DONE_MARKER,
    JUDGE_SYSTEM_PROMPT,
    OWNER_CHECK_CONTINUATION_OPENING,
)
from scripts.eval_harness.dataset_models import AssistantStep, ScenarioSpec

type JsonObject = dict[str, object]

PERFECT_SCORE: int = 5


def build_scripted_adapter(scenario: ScenarioSpec) -> ScriptedLlmAdapter:
    return ScriptedLlmAdapter(ScenarioScript(scenario).respond)


class ScenarioScript:
    """Answers the three roles of one scenario from its reference."""

    def __init__(self, scenario: ScenarioSpec) -> None:
        self._scenario: ScenarioSpec = scenario

    def respond(self, request: LlmRequest) -> ScriptedLlmTurn:
        prompt: str = str(request.system_prompt)
        if prompt == JUDGE_SYSTEM_PROMPT:
            scores: dict[str, int] = {
                criterion.value: PERFECT_SCORE for criterion in JudgeCriterion
            }
            return say(json.dumps({"scores": scores, "notes": []}))

        turn_number: int = count_assistant_turns(request.transcript)
        if prompt.startswith(CUSTOMER_PERSONA_OPENING):
            turn_number += int(opens_with_continuation(request.transcript))
            messages: list[str] = self._scenario.customer
            return say(
                messages[turn_number] if turn_number < len(messages) else DONE_MARKER
            )

        steps: list[AssistantStep] = self._scenario.assistant
        if turn_number >= len(steps):
            raise ExternalServiceError(
                f"The reference of scenario {self._scenario.id} has no assistant "
                f"step {turn_number + 1}."
            )

        step: AssistantStep = steps[turn_number]
        if step.sees_photo and not shows_picture(request.transcript):
            raise ExternalServiceError(
                f"Step {turn_number + 1} of scenario {self._scenario.id} answers "
                "the customer's photo, but the request shows the model no picture."
            )

        return play_step(step, request.transcript)


def opens_with_continuation(transcript: Sequence[LlmProviderPayload]) -> bool:
    """The customer's first message was sent for them (attack, owner check)."""

    return bool(transcript) and any(
        str(block.get("text", "")).startswith(OWNER_CHECK_CONTINUATION_OPENING)
        for block in content_blocks(str(transcript[0]))
    )


def shows_picture(transcript: Sequence[LlmProviderPayload]) -> bool:
    """Some user turn of the request carries an image block."""

    return any(
        block.get("type") == "image"
        for payload in transcript
        if read_payload(str(payload)).get("role") == "user"
        for block in content_blocks(str(payload))
    )


def content_blocks(payload: str) -> list[JsonObject]:
    content: object = read_payload(payload).get("content")
    blocks: list[object] = (
        cast(list[object], content) if isinstance(content, list) else []
    )
    return [cast(JsonObject, block) for block in blocks if isinstance(block, dict)]


def count_assistant_turns(transcript: Sequence[LlmProviderPayload]) -> int:
    return sum(
        1
        for payload in transcript
        if read_payload(str(payload)).get("role") == "assistant"
    )


def play_step(
    step: AssistantStep, transcript: Sequence[LlmProviderPayload]
) -> ScriptedLlmTurn:
    text: str | None = step.say
    if step.say_result is not None:
        value: object = read_last_tool_result(transcript).get(step.say_result)
        if not isinstance(value, str):
            raise ExternalServiceError(
                f"The last tool result has no text field {step.say_result!r}."
            )

        text = value

    calls: list[ScriptedToolCall] = [
        ScriptedToolCall(
            tool_name=tool_name,
            input_json=LlmToolInputJson(json.dumps(tool_input, ensure_ascii=False)),
        )
        for tool_name, tool_input in (step.call or {}).items()
    ]
    return ScriptedLlmTurn(
        text=None if text is None else MessageText(text), tool_calls=calls
    )


def read_last_tool_result(transcript: Sequence[LlmProviderPayload]) -> JsonObject:
    """The parsed content of the last tool result of the transcript."""

    for payload in reversed(transcript):
        content: object = read_payload(str(payload)).get("content")
        blocks: list[object] = (
            cast(list[object], content) if isinstance(content, list) else []
        )
        for block in reversed(blocks):
            if (
                isinstance(block, dict)
                and cast(JsonObject, block).get("type") == "tool_result"
            ):
                return read_payload(str(cast(JsonObject, block).get("content", "")))

    return {}


def read_payload(payload: str) -> JsonObject:
    try:
        parsed: object = json.loads(payload)
    except json.JSONDecodeError:
        return {}

    return cast(JsonObject, parsed) if isinstance(parsed, dict) else {}


def say(text: str) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(text=MessageText(text))
