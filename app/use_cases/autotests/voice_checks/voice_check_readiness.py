"""Whether the voice checks of autotests can run on this server."""

from app.contracts.voice_platform import VoiceCheckAdapterContract
from app.schemas.configurations.app_settings import AppSettings


def are_voice_checks_ready(
    voice_check_adapter: VoiceCheckAdapterContract | None,
    app_settings: AppSettings | None,
) -> bool:
    """
    VOICE_CHECKS_ENABLED is on, the voice platform has its settings
    (ELEVENLABS_API_KEY) and the agents' tool webhooks have APP_BASE_URL:
    then a version with voice is checked by simulated calls. Otherwise its
    autotests are chat only, as before the voice checks (and in production
    a version with voice cannot go live without the voice platform anyway,
    `voice_configuration`).
    """

    return (
        voice_check_adapter is not None
        and app_settings is not None
        and app_settings.voice_agents.are_checks_enabled
        and app_settings.app_base_url is not None
        and not voice_check_adapter.list_missing_settings()
    )
