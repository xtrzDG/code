"""Small builders shared by the evaluation harness tests."""

import json

from app.schemas.constants.assistants import (
    AssistantToolName,
    AutotestScenarioKind,
    LlmEffort,
)
from app.schemas.constants.conversations import LlmStopReason, ReplyGuardVerdict
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.dto.conversation_feed.conversation_views import ToolCallView
from app.schemas.dto.conversations import (
    AssistantReply,
    LlmRequest,
    LlmResponse,
    LlmToolDefinition,
)
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import (
    AutotestScenarioKey,
    LlmModelId,
)
from app.schemas.typings.assistants.strings import (
    AutotestScenarioGoal,
    LlmToolDescription,
    LlmToolInputSchemaJson,
    SystemPromptText,
)
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)
from app.schemas.typings.localization.strings import LanguageDisplayName

SCRIPTS: dict[str, tuple[str, str]] = {
    "en": ("English", "Latn"),
    "ka": ("Georgian", "Geor"),
    "ru": ("Russian", "Cyrl"),
    "he": ("Hebrew", "Hebr"),
    "es": ("Spanish", "Latn"),
}


def scenario(
    language: str = "en",
    kind: AutotestScenarioKind = AutotestScenarioKind.PRICE_QUESTION,
) -> AutotestScenario:
    name, script = SCRIPTS[language]
    return AutotestScenario(
        key=AutotestScenarioKey(f"{kind.value}__{language}"),
        kind=kind,
        language=LanguageTag(language),
        language_name=LanguageDisplayName(name),
        language_script=ScriptCode(script),
        goal=AutotestScenarioGoal("Ask something."),
    )


def tool_call(
    tool_name: AssistantToolName,
    tool_input: dict[str, object] | str,
    result: str = "{}",
    is_error: bool = False,
) -> ToolCallView:
    return ToolCallView(
        tool_name=tool_name,
        input_json=LlmToolInputJson(
            tool_input if isinstance(tool_input, str) else json.dumps(tool_input)
        ),
        result_json=LlmToolResultJson(result),
        is_error=is_error,
    )


def reply(
    text: str | None,
    language: str = "en",
    disclosure: str | None = None,
    tool_calls: list[ToolCallView] | None = None,
    is_handed_off: bool = False,
    guard_verdict: ReplyGuardVerdict = ReplyGuardVerdict.CLEAN,
    booking_count: int = 0,
) -> AssistantReply:
    full_text: str | None = (
        None if text is None else (f"{disclosure}\n{text}" if disclosure else text)
    )
    return AssistantReply(
        conversation_id=ConversationId(),
        text=None if full_text is None else MessageText(full_text),
        disclosure_text=None if disclosure is None else MessageText(disclosure),
        language=LanguageTag(language),
        is_handed_off=is_handed_off,
        guard_verdict=guard_verdict,
        created_booking_ids=[BookingId() for _ in range(booking_count)],
        tool_calls=tool_calls or [],
    )


def tool_definition(
    name: AssistantToolName, description: str = "Does it."
) -> LlmToolDefinition:
    return LlmToolDefinition(
        name=name,
        description=LlmToolDescription(description),
        input_schema_json=LlmToolInputSchemaJson('{"type": "object"}'),
    )


def llm_request(
    transcript: list[str],
    system_prompt: str = "You are the assistant.",
    model: str = "scripted",
    tools: list[LlmToolDefinition] | None = None,
) -> LlmRequest:
    return LlmRequest(
        model_id=LlmModelId(model),
        system_prompt=SystemPromptText(system_prompt),
        tools=tools
        if tools is not None
        else [tool_definition(AssistantToolName.GET_PRICE)],
        transcript=[LlmProviderPayload(payload) for payload in transcript],
        max_output_tokens=LlmMaxOutputTokens(1000),
        effort=LlmEffort.LOW,
    )


def user_turn(text: str) -> str:
    return json.dumps({"role": "user", "content": [{"type": "text", "text": text}]})


def llm_response(text: str) -> LlmResponse:
    return LlmResponse(
        stop_reason=LlmStopReason.END_TURN,
        text=MessageText(text),
        assistant_turn_payload=LlmProviderPayload(
            json.dumps(
                {"role": "assistant", "content": [{"type": "text", "text": text}]}
            )
        ),
    )
