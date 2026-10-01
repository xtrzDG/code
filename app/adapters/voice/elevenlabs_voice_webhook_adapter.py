import json

from typed_time_provider import Microseconds

from app.contracts.channels import VoiceWebhookAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.dto.voice_webhooks import (
    FinishedCallReport,
    FinishedCallTranscriptLine,
    PostCallWebhookRequest,
    VoiceToolCallArguments,
)
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ValidationFailedError,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.channels.constrained_integers import CallOffsetSeconds
from app.schemas.typings.conversations.constrained_integers import (
    CallDurationSeconds,
)
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    MessageText,
    ProviderCallId,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_integer,
    read_number,
    read_object,
    read_objects,
    read_text,
)
from app.utilities.channels.language_codes import from_voice_platform_language
from app.utilities.channels.voice_service import (
    TRANSFER_TOOL_NAME,
)
from app.utilities.channels.webhook_signatures import is_valid_elevenlabs_signature

POST_CALL_TRANSCRIPTION_EVENT: str = "post_call_transcription"
MICROSECONDS_PER_SECOND: int = 1_000_000
MICRO_USD_PER_USD: int = 1_000_000
TRANSCRIPT_AUTHORS: dict[str, MessageAuthor] = {
    "user": MessageAuthor.CUSTOMER,
    "agent": MessageAuthor.ASSISTANT,
}
ASSISTANT_TOOL_NAMES: frozenset[str] = frozenset(
    tool_name.value for tool_name in AssistantToolName
)
# Fields of a tool webhook body that ElevenLabs fills, not the model.
RESERVED_TOOL_FIELDS: frozenset[str] = frozenset(
    {"arguments", "conversation_id", "caller_id", "language"}
)


class ElevenLabsVoiceWebhookAdapter(VoiceWebhookAdapterContract):
    """
    Webhooks of ElevenLabs Agents.

    - Post-call: "ElevenLabs-Signature: t=<unix>,v0=<hex>", HMAC-SHA256 of
      "<t>.<raw body>" with ELEVENLABS_WEBHOOK_SECRET; stale deliveries
      (more than 30 minutes) are rejected. Only "post_call_transcription"
      events describe a finished call; cost comes from `cost_fiat` (USD).
    - Tool calls: the body the agent's webhook tools send ("arguments",
      "conversation_id", "caller_id", "language").
    - Call initiation: {"caller_id", "agent_id", "called_number", "call_sid"}.
    """

    def __init__(self, app_settings: AppSettings) -> None:
        self._app_settings: AppSettings = app_settings

    def verify_post_call_signature(
        self,
        request: PostCallWebhookRequest,
        now: Microseconds,
    ) -> None:
        webhook_secret: PlatformSecret | None = (
            self._app_settings.elevenlabs_webhook_secret
        )
        if webhook_secret is None or not is_valid_elevenlabs_signature(
            webhook_secret,
            request.body,
            request.signature_header,
            int(now) // MICROSECONDS_PER_SECOND,
        ):
            raise AuthenticationRequiredError(
                "The ElevenLabs signature is missing, wrong or too old."
            )

    def parse_post_call(self, body: bytes) -> FinishedCallReport | None:
        root: JsonObject | None = parse_json_object(body)
        if root is None:
            raise ValidationFailedError("The post-call webhook is not a JSON object.")

        if read_text(root, "type") != POST_CALL_TRANSCRIPTION_EVENT:
            return None

        data: JsonObject | None = read_object(root, "data")
        conversation_id: str | None = (
            None if data is None else read_text(data, "conversation_id")
        )
        if data is None or conversation_id is None:
            raise ValidationFailedError("The post-call webhook has no conversation.")

        metadata: JsonObject = read_object(data, "metadata") or {}
        started_at_seconds: int | None = read_integer(
            metadata, "start_time_unix_secs"
        ) or read_integer(root, "event_timestamp")
        if started_at_seconds is None or started_at_seconds < 0:
            raise ValidationFailedError("The post-call webhook has no start time.")

        phone_call: JsonObject = read_object(metadata, "phone_call") or {}
        dynamic_variables: JsonObject = read_dynamic_variables(data)
        agent_id: str | None = read_text(data, "agent_id")
        transcript_items: list[JsonObject] = read_objects(data, "transcript")
        return FinishedCallReport(
            provider_call_id=ProviderCallId(conversation_id),
            agent_id=None if agent_id is None else VoiceAgentId(agent_id),
            assistant_number=read_raw_number(
                phone_call, "agent_number", dynamic_variables, "system__called_number"
            ),
            caller_number=read_raw_number(
                phone_call, "external_number", dynamic_variables, "system__caller_id"
            ),
            started_at=Microseconds(started_at_seconds * MICROSECONDS_PER_SECOND),
            duration_seconds=CallDurationSeconds(
                max(read_integer(metadata, "call_duration_secs") or 0, 0)
            ),
            transcript=read_transcript(transcript_items),
            called_tools=read_called_tools(transcript_items),
            cost_micro_usd=read_cost(metadata),
            language=read_call_language(metadata, data),
            has_recording=data.get("has_audio") is not False,
            transfer_offset_seconds=read_transfer_offset(transcript_items),
        )

    def parse_tool_call(self, body: bytes) -> VoiceToolCallArguments:
        root: JsonObject | None = parse_json_object(body)
        if root is None:
            raise ValidationFailedError("The tool call is not a JSON object.")

        conversation_id: str | None = read_text(root, "conversation_id")
        if conversation_id is None:
            raise ValidationFailedError("The tool call has no conversation_id.")

        arguments: JsonObject | None = read_object(root, "arguments")
        if arguments is None:
            if "arguments" in root and root["arguments"] is not None:
                raise ValidationFailedError("Tool call arguments must be an object.")

            arguments = {
                key: value
                for key, value in root.items()
                if key not in RESERVED_TOOL_FIELDS
            }

        caller_id: str | None = read_text(root, "caller_id")
        raw_language: str | None = read_text(root, "language")
        return VoiceToolCallArguments(
            input_json=LlmToolInputJson(json.dumps(arguments, ensure_ascii=False)),
            provider_call_id=ProviderCallId(conversation_id),
            caller_number=None if caller_id is None else RawPhoneNumberInput(caller_id),
            language=(
                None
                if raw_language is None
                else from_voice_platform_language(raw_language)
            ),
        )

    def parse_call_initiation(self, body: bytes) -> RawPhoneNumberInput | None:
        root: JsonObject | None = parse_json_object(body)
        if root is None:
            raise ValidationFailedError("The call initiation is not a JSON object.")

        caller_id: str | None = read_text(root, "caller_id")
        return None if caller_id is None else RawPhoneNumberInput(caller_id)


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
