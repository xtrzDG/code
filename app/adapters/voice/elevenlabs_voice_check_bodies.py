"""
The bodies of the voice checks at ElevenLabs agent testing: the agent the
checks talk to, one simulated call (a test of type "simulation") and the
result of a test run read back.
"""

from app.adapters.voice.elevenlabs_agent_config import (
    AGENT_TAG,
    MAX_AGENT_NAME_LENGTH,
    build_agent_config,
)
from app.adapters.voice.elevenlabs_post_call_reading import (
    ASSISTANT_TOOL_NAMES,
    TRANSCRIPT_AUTHORS,
    read_cost,
)
from app.contracts.channel_clients import JsonObject
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.voice_checks import VoiceCheckStatus
from app.schemas.dto.voice import VoiceAgentSpec
from app.schemas.dto.voice_checks import (
    VoiceCheckCase,
    VoiceCheckLine,
    VoiceCheckOutcome,
    VoiceCheckToolCall,
)
from app.schemas.typings.channels.strings import VoicePlatformToolId
from app.schemas.typings.conversations.strings import LlmToolInputJson, MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.voice.strings import VoiceCheckRationale
from app.utilities.channels.json_values import (
    read_object,
    read_objects,
    read_strings,
    read_text,
)
from app.utilities.channels.voice_service import (
    CALL_VARIABLE_PLACEHOLDERS,
    LOCAL_NOW_VARIABLE,
    NEXT_DAYS_VARIABLE,
    TIMEZONE_VARIABLE,
)

VOICE_CHECK_TAG: str = "voice-check"
# A booking takes about a dozen turns on the phone; a simulated call that
# needs more has lost its way.
SIMULATION_MAX_TURNS: int = 16
RUN_STATUSES: dict[str, VoiceCheckStatus | None] = {
    "pending": None,
    "passed": VoiceCheckStatus.PASSED,
    "failed": VoiceCheckStatus.FAILED,
    "cancelled": VoiceCheckStatus.ERRORED,
}


def build_check_agent_config(
    spec: VoiceAgentSpec,
    tool_ids: list[VoicePlatformToolId],
    request_headers: JsonObject,
    language: LanguageTag,
) -> JsonObject:
    """
    The business's agent as `spec` builds it, answering in `language`
    first (its greeting, its voice): named and tagged as a voice check,
    without the call-initiation webhook (no real call reaches it).
    """

    config: JsonObject = build_agent_config(
        spec.model_copy(update={"default_language": language}),
        tool_ids,
        request_headers,
    )
    platform: JsonObject = dict(read_object(config, "platform_settings") or {})
    platform.pop("workspace_overrides", None)
    platform.pop("overrides", None)
    return {
        **config,
        "name": f"Voice check: {spec.business_name} ({spec.business_id})"[
            :MAX_AGENT_NAME_LENGTH
        ],
        "tags": [AGENT_TAG, VOICE_CHECK_TAG, str(spec.business_id)],
        "platform_settings": platform,
    }


def agent_config_override(config: JsonObject) -> JsonObject:
    """What `run-tests` takes instead of the agent's own configuration."""

    return {
        "conversation_config": config["conversation_config"],
        "platform_settings": config["platform_settings"],
    }


def build_test_config(case: VoiceCheckCase) -> JsonObject:
    """
    One simulated call: the caller's brief and the condition it must meet,
    the "Current call" variables, and every tool mocked (one that has no
    mock fails instead of running).
    """

    variables: dict[str, str] = {
        **CALL_VARIABLE_PLACEHOLDERS,
        LOCAL_NOW_VARIABLE: str(case.call_context.local_now_text),
        NEXT_DAYS_VARIABLE: str(case.call_context.next_days_text),
        TIMEZONE_VARIABLE: str(case.call_context.timezone),
    }
    return {
        "type": "simulation",
        "name": f"Voice check {case.key}",
        "simulation_scenario": str(case.brief),
        "success_conditions": [str(case.condition)],
        "simulation_max_turns": SIMULATION_MAX_TURNS,
        "dynamic_variables": dict(variables),
        "tool_mock_config": {
            "mocking_strategy": "all",
            "fallback_strategy": "raise_error",
        },
        "tool_mock_overrides": {
            mock.tool_name.value: [
                {"mock_result": str(mock.result_json), "is_error": False}
            ]
            for mock in case.tool_mocks
        },
    }


def read_run_status(run: JsonObject) -> VoiceCheckStatus | None:
    """The run's status; None while it is pending, ERRORED when unknown."""

    raw: str = (read_text(run, "status") or "").lower()
    return RUN_STATUSES.get(raw, VoiceCheckStatus.ERRORED)


def read_test_run(case: VoiceCheckCase, run: JsonObject) -> VoiceCheckOutcome:
    """A finished run of the case's test: lines, tools, reasons and cost."""

    responses: list[JsonObject] = read_objects(run, "agent_responses")
    return VoiceCheckOutcome(
        key=case.key,
        status=read_run_status(run) or VoiceCheckStatus.UNFINISHED,
        lines=read_lines(responses),
        tool_calls=read_tool_calls(responses),
        rationale=read_rationale(run),
        cost_micro_usd=read_cost(run),
    )


def read_lines(responses: list[JsonObject]) -> list[VoiceCheckLine]:
    lines: list[VoiceCheckLine] = []
    for response in responses:
        author: MessageAuthor | None = TRANSCRIPT_AUTHORS.get(
            read_text(response, "role") or ""
        )
        text: str | None = read_text(response, "message")
        if author is not None and text is not None:
            lines.append(VoiceCheckLine(author=author, text=MessageText(text.strip())))

    return lines


def read_tool_calls(responses: list[JsonObject]) -> list[VoiceCheckToolCall]:
    """The assistant tools the agent called, in order, with their arguments."""

    calls: list[VoiceCheckToolCall] = []
    for response in responses:
        for tool_call in read_objects(response, "tool_calls"):
            tool_name: str | None = read_text(tool_call, "tool_name")
            if tool_name is None or tool_name not in ASSISTANT_TOOL_NAMES:
                continue

            calls.append(
                VoiceCheckToolCall(
                    tool_name=AssistantToolName(tool_name),
                    input_json=LlmToolInputJson(
                        read_text(tool_call, "params_as_json") or "{}"
                    ),
                )
            )

    return calls


def read_rationale(run: JsonObject) -> list[VoiceCheckRationale]:
    """The evaluator's summary and reasons, without repeats."""

    condition: JsonObject = read_object(run, "condition_result") or {}
    rationale: JsonObject = read_object(condition, "rationale") or {}
    texts: list[str] = [
        text.strip()
        for text in [
            read_text(rationale, "summary"),
            *read_strings(rationale, "messages"),
        ]
        if text is not None and text.strip()
    ]
    return [VoiceCheckRationale(text) for text in dict.fromkeys(texts)]
