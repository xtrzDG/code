"""Choose who transcribes customers' voice notes."""

from app.adapters.media.openai_voice_transcriber_adapter import (
    OpenAiVoiceTranscriberAdapter,
)
from app.adapters.media.unavailable_voice_transcriber_adapter import (
    UnavailableVoiceTranscriberAdapter,
)
from app.contracts.channel_media import VoiceTranscriberContract
from app.contracts.llm_clients import OpenAiTranscriptionClientContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import LlmProvider


def build_voice_transcriber(
    settings: AppSettings,
    client: OpenAiTranscriptionClientContract,
) -> VoiceTranscriberContract:
    """
    OpenAI's speech-to-text in the EU project (LLM_TRANSCRIBE_MODEL);
    nothing with the offline model (LLM_PROVIDER=scripted), where voice
    notes get the polite request to write.
    """

    if settings.llm_provider is LlmProvider.SCRIPTED:
        return UnavailableVoiceTranscriberAdapter()

    return OpenAiVoiceTranscriberAdapter(client)
