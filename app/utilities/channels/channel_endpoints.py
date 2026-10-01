"""Public webhook addresses and header names of the channels module.

Routes serve these paths and the code that registers webhooks with the
platforms (Telegram setWebhook, the ElevenLabs agent) builds the same
addresses from APP_BASE_URL, so both always agree.
"""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.typings.channels.prefixed_id import ChannelId

TELEGRAM_WEBHOOK_PATH_TEMPLATE: str = "/v1/channels/telegram/{channel_id}/webhook"
TELEGRAM_PLATFORM_WEBHOOK_PATH: str = "/v1/channels/telegram-platform/webhook"
META_WEBHOOK_PATH: str = "/v1/channels/meta/webhook"
VOICE_TOOL_PATH_TEMPLATE: str = "/v1/voice/tools/{tool_name}"
VOICE_CALL_INITIATION_PATH: str = "/v1/voice/webhooks/conversation-initiation"
VOICE_POST_CALL_PATH: str = "/v1/voice/webhooks/post-call"
WIDGET_SCRIPT_PATH: str = "/widget.js"

TELEGRAM_SECRET_HEADER: str = "X-Telegram-Bot-Api-Secret-Token"
META_SIGNATURE_HEADER: str = "X-Hub-Signature-256"
ELEVENLABS_SIGNATURE_HEADER: str = "ElevenLabs-Signature"
VOICE_BUSINESS_ID_HEADER: str = "X-Assistant-Business-Id"
VOICE_TOOL_SECRET_HEADER: str = "X-Assistant-Tool-Secret"
VOICE_BODY_SIGNATURE_HEADER: str = "X-Assistant-Signature"


def join_public_url(base_url: str, path: str) -> str:
    """APP_BASE_URL (with or without a trailing slash) joined with a path."""

    return base_url.rstrip("/") + path


def build_telegram_webhook_path(channel_id: ChannelId) -> str:
    return TELEGRAM_WEBHOOK_PATH_TEMPLATE.format(channel_id=channel_id)


def build_voice_tool_path(tool_name: AssistantToolName) -> str:
    return VOICE_TOOL_PATH_TEMPLATE.format(tool_name=tool_name.value)
