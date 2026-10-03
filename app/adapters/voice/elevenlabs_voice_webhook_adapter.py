import json

from typed_time_provider import Microseconds

from app.adapters.voice.elevenlabs_post_call_reading import (
    read_call_language,
    read_called_tools,
    read_cost,
    read_dynamic_variables,
    read_failed_start_numbers,
    read_raw_number,
    read_transcript,
    read_transfer_offset,
    read_transfer_outcome,
)
from app.contracts.channels import VoiceWebhookAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.calls import MissedCallReason, MissedCallSource
from app.schemas.dto.calls.missed_calls import MissedCallReport
from app.schemas.dto.voice_webhooks import (
    FinishedCallReport,
    PostCallWebhookRequest,
    VoiceToolCallArguments,
)
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ValidationFailedError,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.conversations.constrained_integers import (
    CallDurationSeconds,
)
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    ProviderCallId,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_integer,
    read_object,
    read_objects,
    read_text,
)
from app.utilities.channels.language_codes import from_voice_platform_language
from app.utilities.channels.webhook_signatures import is_valid_elevenlabs_signature

POST_CALL_TRANSCRIPTION_EVENT: str = "post_call_transcription"
CALL_INITIATION_FAILURE_EVENT: str = "call_initiation_failure"
MICROSECONDS_PER_SECOND: int = 1_000_000
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
      "call_initiation_failure" events describe a call the platform could
      not start (its caller did not get through).
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
            transfer_outcome=read_transfer_outcome(transcript_items),
        )

    def parse_call_start_failure(self, body: bytes) -> MissedCallReport | None:
        root: JsonObject | None = parse_json_object(body)
        if root is None or read_text(root, "type") != CALL_INITIATION_FAILURE_EVENT:
            return None

        data: JsonObject = read_object(root, "data") or {}
        conversation_id: str | None = read_text(data, "conversation_id")
        started_at_seconds: int | None = read_integer(root, "event_timestamp")
        if conversation_id is None or started_at_seconds is None:
            raise ValidationFailedError("The failed call start names no call.")

        caller_number, called_number = read_failed_start_numbers(data)
        return MissedCallReport(
            source=MissedCallSource.VOICE_PLATFORM,
            provider_call_id=ProviderCallId(conversation_id),
            reason=MissedCallReason.NOT_STARTED,
            called_at=Microseconds(
                max(started_at_seconds, 0) * MICROSECONDS_PER_SECOND
            ),
            assistant_number=called_number,
            caller_number=caller_number,
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
