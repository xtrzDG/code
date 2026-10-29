import math

from openai.types.audio import Transcription
from openai.types.audio.transcription import UsageDuration

from app.contracts.channel_media import VoiceTranscriberContract
from app.contracts.llm_clients import OpenAiTranscriptionClientContract
from app.schemas.dto.media import VoiceTranscriptionInput, VoiceTranscriptionResult
from app.schemas.typings.media.constrained_integers import AudioDurationSeconds
from app.schemas.typings.media.strings import TranscribedVoiceText
from app.utilities.media.media_paths import FILE_EXTENSIONS

# Models that take a list of possible languages and keywords; the others
# take one language at most.
MULTI_LANGUAGE_MODEL_PREFIXES: tuple[str, ...] = ("gpt-transcribe",)
MAX_KEYWORDS: int = 10


class OpenAiVoiceTranscriberAdapter(VoiceTranscriberContract):
    """
    Voice notes transcribed by OpenAI (LLM_TRANSCRIBE_MODEL) in the EU
    project. The assistant's languages are the hint: models that take a
    list get all of them and the business name as a keyword; the others
    get the language when the assistant speaks only one, and recognize it
    themselves otherwise.
    """

    def __init__(self, client: OpenAiTranscriptionClientContract) -> None:
        self._client: OpenAiTranscriptionClientContract = client

    def transcribe(self, request: VoiceTranscriptionInput) -> VoiceTranscriptionResult:
        model: str = str(request.model_id)
        base_languages: list[str] = unique_base_languages(
            [str(tag) for tag in request.language_hints]
        )
        takes_hints: bool = model.startswith(MULTI_LANGUAGE_MODEL_PREFIXES)
        extension: str = FILE_EXTENSIONS.get(str(request.audio.media_type), "ogg")
        transcription: Transcription = self._client.transcribe(
            model=model,
            audio=request.audio.content,
            file_name=f"voice.{extension}",
            language=(
                base_languages[0]
                if len(base_languages) == 1 and not takes_hints
                else None
            ),
            languages=base_languages if takes_hints else [],
            keywords=(
                [str(word) for word in request.keywords][:MAX_KEYWORDS]
                if takes_hints
                else []
            ),
        )
        usage = transcription.usage
        return VoiceTranscriptionResult(
            text=TranscribedVoiceText(transcription.text.strip()),
            billed_seconds=(
                AudioDurationSeconds(math.ceil(usage.seconds))
                if isinstance(usage, UsageDuration) and usage.seconds >= 0
                else None
            ),
        )


def unique_base_languages(language_tags: list[str]) -> list[str]:
    """ISO 639-1 codes of the tags ("ka-GE" -> "ka"), first come first."""

    codes: list[str] = []
    for tag in language_tags:
        code: str = tag.split("-", 1)[0].lower()
        if len(code) == 2 and code not in codes:
            codes.append(code)

    return codes
