"""
Reading the post-call webhooks of ElevenLabs Agents: the parts of a
finished call's report (transcript, tools, transfer, cost, language) and a
call the platform could not start.
"""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.calls import CallTransferOutcome
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.channels.constrained_integers import CallOffsetSeconds
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.utilities.channels.json_values import (
    JsonObject,
    read_integer,
    read_number,
    read_object,
    read_objects,
    read_text,
)
from app.utilities.channels.language_codes import from_voice_platform_language
from app.utilities.channels.voice_service import TRANSFER_TOOL_NAME

MICRO_USD_PER_USD: int = 1_000_000
TRANSCRIPT_AUTHORS: dict[str, MessageAuthor] = {
    "user": MessageAuthor.CUSTOMER,
    "agent": MessageAuthor.ASSISTANT,
}
ASSISTANT_TOOL_NAMES: frozenset[str] = frozenset(
    tool_name.value for tool_name in AssistantToolName
)
# Words of a transfer's tool result that say nobody took the call.
TRANSFER_FAILURE_MARKERS: tuple[str, ...] = (
    "no-answer",
    "no answer",
    "no_answer",
    "busy",
    "failed",
    "not answered",
    "unanswered",
    "declined",
)
# Where a failed start names the numbers: Twilio's status callback, or the
# SIP and platform fields.
CALLER_FIELDS: tuple[str, ...] = ("From", "from", "from_number", "caller_id")
CALLED_FIELDS: tuple[str, ...] = (
    "To",
    "Called",
    "to",
    "to_number",
    "called_number",
    "agent_number",
)


def read_dynamic_variables(data: JsonObject) -> JsonObject:
    client_data: JsonObject = (
        read_object(data, "conversation_initiation_client_data") or {}
    )
    return read_object(client_data, "dynamic_variables") or {}


def read_raw_number(
    phone_call: JsonObject,
    phone_call_key: str,
    dynamic_variables: JsonObject,
    variable_key: str,
) -> RawPhoneNumberInput | None:
    raw_number: str | None = read_text(phone_call, phone_call_key) or read_text(
        dynamic_variables, variable_key
    )
    return None if raw_number is None else RawPhoneNumberInput(raw_number)


def read_transcript(items: list[JsonObject]) -> list[FinishedCallTranscriptLine]:
    lines: list[FinishedCallTranscriptLine] = []
    for item in items:
        author: MessageAuthor | None = TRANSCRIPT_AUTHORS.get(
            read_text(item, "role") or ""
        )
        text: str | None = read_text(item, "message")
        if author is None or text is None:
            continue

        lines.append(
            FinishedCallTranscriptLine(
                author=author,
                text=MessageText(text.strip()),
                offset_seconds=CallOffsetSeconds(
                    max(read_integer(item, "time_in_call_secs") or 0, 0)
                ),
            )
        )

    return lines


def read_called_tools(items: list[JsonObject]) -> list[AssistantToolName]:
    """Assistant tools the agent called, in first-call order."""

    tool_names: list[AssistantToolName] = []
    for item in items:
        for tool_call in read_objects(item, "tool_calls"):
            tool_name: str | None = read_text(tool_call, "tool_name")
            if tool_name not in ASSISTANT_TOOL_NAMES:
                continue

            assistant_tool: AssistantToolName = AssistantToolName(tool_name)
            if assistant_tool not in tool_names:
                tool_names.append(assistant_tool)

    return tool_names


def read_transfer_offset(items: list[JsonObject]) -> CallOffsetSeconds | None:
    """Seconds into the call when the agent put the caller through to staff."""

    for item in items:
        for tool_call in read_objects(item, "tool_calls"):
            if read_text(tool_call, "tool_name") == TRANSFER_TOOL_NAME:
                return CallOffsetSeconds(
                    max(read_integer(item, "time_in_call_secs") or 0, 0)
                )

    return None


def read_cost(metadata: JsonObject) -> CostMicroUsd:
    """Call cost in micro-USD: `cost_fiat`, else LLM plus platform price."""

    cost_usd: float | None = read_number(metadata, "cost_fiat")
    if cost_usd is None:
        charging: JsonObject = read_object(metadata, "charging") or {}
        llm_price: float | None = read_number(charging, "llm_price")
        platform_price: float | None = read_number(charging, "platform_price")
        if llm_price is not None or platform_price is not None:
            cost_usd = (llm_price or 0.0) + (platform_price or 0.0)

    if cost_usd is None or cost_usd <= 0:
        return CostMicroUsd(0)

    return CostMicroUsd(round(cost_usd * MICRO_USD_PER_USD))


def read_call_language(metadata: JsonObject, data: JsonObject) -> LanguageTag | None:
    raw_language: str | None = read_text(metadata, "main_language")
    if raw_language is None:
        client_data: JsonObject = (
            read_object(data, "conversation_initiation_client_data") or {}
        )
        override: JsonObject = (
            read_object(client_data, "conversation_config_override") or {}
        )
        raw_language = read_text(read_object(override, "agent") or {}, "language")

    return None if raw_language is None else from_voice_platform_language(raw_language)


def read_transfer_outcome(items: list[JsonObject]) -> CallTransferOutcome:
    """
    Whether the caller the agent put through to staff got a person: the
    transfer's tool result is an error or says nobody answered, or the
    caller went on talking to the agent afterwards (UNANSWERED); a transfer
    without either is CONNECTED.
    """

    start: int | None = next(
        (
            index
            for index, item in enumerate(items)
            for tool_call in read_objects(item, "tool_calls")
            if read_text(tool_call, "tool_name") == TRANSFER_TOOL_NAME
        ),
        None,
    )
    if start is None:
        return CallTransferOutcome.NOT_TRANSFERRED

    for item in items[start:]:
        for result in read_objects(item, "tool_results"):
            if read_text(result, "tool_name") != TRANSFER_TOOL_NAME:
                continue

            value: str = (read_text(result, "result_value") or "").lower()
            if result.get("is_error") is True or any(
                marker in value for marker in TRANSFER_FAILURE_MARKERS
            ):
                return CallTransferOutcome.UNANSWERED

    if any(
        read_text(item, "role") == "user" and read_text(item, "message")
        for item in items[start + 1 :]
    ):
        return CallTransferOutcome.UNANSWERED

    return CallTransferOutcome.CONNECTED


def read_failed_start_numbers(
    data: JsonObject,
) -> tuple[RawPhoneNumberInput | None, RawPhoneNumberInput | None]:
    """The caller's and the called number of a call that failed to start."""

    metadata: JsonObject = read_object(data, "metadata") or {}
    body: JsonObject = read_object(metadata, "body") or {}
    sources: list[JsonObject] = [body, metadata, data]
    return (
        first_number(sources, CALLER_FIELDS),
        first_number(sources, CALLED_FIELDS),
    )


def first_number(
    sources: list[JsonObject],
    fields: tuple[str, ...],
) -> RawPhoneNumberInput | None:
    for source in sources:
        for field in fields:
            value: str | None = read_text(source, field)
            if value is not None and value.strip():
                return RawPhoneNumberInput(value.strip())

    return None
