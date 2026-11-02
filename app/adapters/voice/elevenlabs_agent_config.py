"""
The ElevenLabs agent of a business: languages, greetings, built-in tools,
the "Current call" block the call-initiation webhook fills in per call, its
tuning (model, voices, speech recognition, turn timeout), the evaluation of
every call, the call caps (the longest call, the silence that ends one, the
calls at once and in a day) and its authentication: a conversation starts
only through the business's phone number or a signed URL made with the
platform's API key, never from a browser that found the agent's id.
"""

from app.adapters.voice.elevenlabs_agent_tuning import (
    asr_config,
    build_language_presets,
    find_profile,
    tts_config,
    turn_config,
)
from app.adapters.voice.elevenlabs_call_analysis import build_analysis_settings
from app.contracts.channel_clients import JsonObject
from app.schemas.dto.spend_guard import VoiceCallLimits
from app.schemas.dto.voice import VoiceAgentSpec, VoiceGreeting, VoiceProfile
from app.schemas.typings.channels.strings import VoicePlatformToolId
from app.utilities.channels.channel_endpoints import (
    VOICE_CALL_INITIATION_PATH,
    join_public_url,
)
from app.utilities.channels.language_codes import to_voice_platform_language
from app.utilities.channels.voice_service import (
    CALL_VARIABLE_PLACEHOLDERS,
    LOCAL_NOW_VARIABLE,
    MAX_CONCURRENT_CALLS,
    MAX_DAILY_CALLS,
    NEXT_DAYS_VARIABLE,
    NO_TRANSFER_VALUE,
    OPEN_NOW_VARIABLE,
    OPEN_NOW_YES,
    TIMEZONE_VARIABLE,
    TRANSFER_NUMBER_VARIABLE,
    TRANSFER_TOOL_NAME,
    UNKNOWN_VALUE,
)

AGENT_TAG: str = "assistant-workshop"
MAX_AGENT_NAME_LENGTH: int = 120
# Concept sections 1 and 6: during opening hours a caller who asks for a
# person is put through to staff; outside them the agent hands off and a
# colleague calls back. The call-initiation webhook sets is_open_now and
# the destination, transfer_number: the staff mobile only while the
# business is open, else "none", so the platform has nowhere to dial.
TRANSFER_TOOL_DESCRIPTION: str = (
    "Put the caller through to a staff member of the business."
)


def placeholder(variable_name: str) -> str:
    """How the agent's prompt refers to a per-call variable: {{name}}."""

    return "{{" + variable_name + "}}"


TRANSFER_CONDITION: str = (
    "The caller asks to talk to a person (an operator, a manager, a staff "
    "member), the business is open now and a transfer number is set: "
    f"is_open_now is '{placeholder(OPEN_NOW_VARIABLE)}' and must be "
    f"'{OPEN_NOW_YES}', and transfer_number is "
    f"'{placeholder(TRANSFER_NUMBER_VARIABLE)}' and must not be "
    f"'{NO_TRANSFER_VALUE}'. Otherwise never transfer: use handoff_to_human "
    "so a colleague calls back."
)
# Signed URLs only: no allowed host, and a connection without an origin is
# refused too. Phone calls through the business's number are not affected.
AGENT_AUTH: JsonObject = {
    "enable_auth": True,
    "allowlist": [],
    "require_origin_header": True,
}


# Appended to the phone instruction: what the call-initiation webhook fills
# in for every call (the instruction itself has no date, for the cache).
CURRENT_CALL_SECTION: str = "\n".join(
    [
        "# Current call",
        "The platform fills in these lines when the call starts.",
        f"- Local date and time at the business: {placeholder(LOCAL_NOW_VARIABLE)} "
        f"({placeholder(TIMEZONE_VARIABLE)}).",
        f"- The next days: {placeholder(NEXT_DAYS_VARIABLE)}.",
        f"- The business is open now: {placeholder(OPEN_NOW_VARIABLE)}.",
        f"- Staff can take the call: {placeholder(TRANSFER_NUMBER_VARIABLE)} "
        f"({NO_TRANSFER_VALUE}: nobody can, hand off instead).",
        'Turn "today", "tomorrow" or a weekday into a YYYY-MM-DD date from these '
        "lines before you call a tool, and say the date back to the caller. When "
        f"the local date is {UNKNOWN_VALUE}, ask the caller for the exact date.",
        "The number a call comes from proves nobody's identity. Never say "
        "whether someone has a booking, never read one out, and never cancel or "
        "move one on the phone: offer to pass the request to a colleague with "
        "handoff_to_human, who calls back the number on the booking; the "
        "customer can also use the link in their booking confirmation. New "
        "bookings are fine.",
        "If the caller reports an emergency or a danger to health or life, say "
        "first, before anything else, that they should hang up and call the "
        "emergency number from the Emergencies section now; then hand off with "
        "urgency critical. Never put an emergency through to staff instead.",
    ]
)


def build_agent_config(
    spec: VoiceAgentSpec,
    tool_ids: list[VoicePlatformToolId],
    request_headers: JsonObject,
    call_limits: VoiceCallLimits | None = None,
) -> JsonObject:
    """
    Create / update body of the business's agent: its instruction and
    tools, the language model and temperature, the voice of the default
    language (the other languages' voices and greetings in their presets),
    the speech recognition's keywords, the turn timeout, the evaluation of
    every call (`build_analysis_settings`) and the call caps: every call
    ends at `call_limits.max_duration_seconds` and after
    `call_limits.silence_end_seconds` of silence (the defaults: 10 minutes
    and 30 seconds), and the agent takes at most MAX_CONCURRENT_CALLS calls
    at once and MAX_DAILY_CALLS a day (no paid bursting). The agent's
    authentication (`AGENT_AUTH`) lets no web or WebSocket conversation
    start without a signed URL.
    """

    limits: VoiceCallLimits = call_limits or VoiceCallLimits()
    default_greeting: VoiceGreeting | None = find_greeting(spec)
    agent: JsonObject = {
        "language": to_voice_platform_language(spec.default_language),
        "prompt": {
            "prompt": f"{spec.prompt_text}\n\n{CURRENT_CALL_SECTION}",
            "llm": str(spec.llm_model),
            "temperature": float(spec.temperature),
            "tool_ids": [str(tool_id) for tool_id in tool_ids],
            "built_in_tools": build_built_in_tools(spec),
        },
        # Set per call by the call-initiation webhook; closed and unknown
        # until then.
        "dynamic_variables": {
            "dynamic_variable_placeholders": dict(CALL_VARIABLE_PLACEHOLDERS)
        },
    }
    if default_greeting is not None:
        agent["first_message"] = str(default_greeting.text)

    conversation_config: JsonObject = {
        "agent": agent,
        "asr": asr_config(spec),
        "conversation": {"max_duration_seconds": int(limits.max_duration_seconds)},
        "turn": turn_config(spec, limits),
    }
    default_profile: VoiceProfile | None = find_profile(spec, spec.default_language)
    if default_profile is not None:
        conversation_config["tts"] = tts_config(default_profile)

    language_presets: JsonObject = build_language_presets(spec)
    if language_presets:
        conversation_config["language_presets"] = language_presets

    return {
        "name": f"{spec.business_name} ({spec.business_id})"[:MAX_AGENT_NAME_LENGTH],
        "tags": [AGENT_TAG, str(spec.business_id)],
        "conversation_config": conversation_config,
        "platform_settings": {
            **build_analysis_settings(),
            "auth": dict(AGENT_AUTH),
            "call_limits": {
                "agent_concurrency_limit": MAX_CONCURRENT_CALLS,
                "daily_limit": MAX_DAILY_CALLS,
                "bursting_enabled": False,
            },
            "overrides": {
                "enable_conversation_initiation_client_data_from_webhook": True,
                "conversation_config_override": {
                    "agent": {"first_message": True, "language": True}
                },
            },
            "workspace_overrides": {
                "conversation_initiation_client_data_webhook": {
                    "url": join_public_url(
                        str(spec.tool_webhook_base_url),
                        VOICE_CALL_INITIATION_PATH,
                    ),
                    "request_headers": dict(request_headers),
                }
            },
        },
    }


def build_built_in_tools(spec: VoiceAgentSpec) -> JsonObject:
    """
    Ending the call; the transfer to staff when the business has a staff
    mobile (dialled only as the call's transfer_number); language detection
    when the agent speaks more than one language.
    """

    built_in_tools: JsonObject = {
        "end_call": {
            "type": "system",
            "name": "end_call",
            "params": {"system_tool_type": "end_call"},
        }
    }
    if spec.transfer_phone_number is not None:
        built_in_tools[TRANSFER_TOOL_NAME] = {
            "type": "system",
            "name": TRANSFER_TOOL_NAME,
            "description": TRANSFER_TOOL_DESCRIPTION,
            "params": {
                "system_tool_type": TRANSFER_TOOL_NAME,
                # The destination is the call's transfer_number variable,
                # never a number fixed in the agent (see TRANSFER_CONDITION).
                "transfers": [
                    {
                        "transfer_destination": {
                            "type": "phone_dynamic_variable",
                            "phone_number": TRANSFER_NUMBER_VARIABLE,
                        },
                        "condition": TRANSFER_CONDITION,
                    }
                ],
                "enable_client_message": True,
            },
        }

    if len({to_voice_platform_language(tag) for tag in spec.languages}) > 1:
        built_in_tools["language_detection"] = {
            "type": "system",
            "name": "language_detection",
            "params": {"system_tool_type": "language_detection"},
        }

    return built_in_tools


def find_greeting(spec: VoiceAgentSpec) -> VoiceGreeting | None:
    """Greeting in the default language, else the first one."""

    for greeting in spec.greetings:
        if greeting.language == spec.default_language:
            return greeting

    return spec.greetings[0] if spec.greetings else None
