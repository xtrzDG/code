import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.channel_media import VoiceTranscriberContract
from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.billing_repositories import UsageEventRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.media_repositories import MessageMediaRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.media_settings import MediaSettings
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.media import AttachmentKind, AttachmentProblem
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.message_media import MessageAttachment, MessageMediaDocument
from app.schemas.dto.media import (
    MediaLocation,
    StoredMediaFile,
    VoiceNoteTranscription,
    VoiceNoteTranscriptionRequest,
    VoiceTranscriptionInput,
    VoiceTranscriptionResult,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.media_errors import TranscriptionNotConfiguredError
from app.schemas.typings.billing.constrained_integers import UsageQuantity
from app.schemas.typings.media.constrained_integers import AudioDurationSeconds
from app.schemas.typings.media.strings import TranscribedVoiceText
from app.use_cases.conversations.voice_note_hints import (
    estimate_duration_seconds,
    read_language_hints,
)
from app.utilities.media.transcription_pricing import transcription_cost

logger: logging.Logger = logging.getLogger(__name__)
# Longer transcripts are cut, like typed messages: no customer needs more.
MAX_TRANSCRIPT_LENGTH: int = 4000


class TranscribeVoiceNoteUseCase(
    UseCaseContract[VoiceNoteTranscriptionRequest, VoiceNoteTranscription]
):
    """
    Turn a customer's stored voice note into text (speech-to-text in the
    EU, LLM_TRANSCRIBE_MODEL), with the assistant's languages as the hint
    and the business name as a word to expect.

    A transcript an earlier attempt kept is returned as it is (one charge
    per voice note). A voice note over MEDIA_MAX_VOICE_SECONDS is not sent
    (TOO_LONG); one without words is NOT_UNDERSTOOD, and so is every voice
    note while no speech-to-text is configured. A temporary failure fails
    the job to try again; its last attempt gives the voice note up. Each
    transcription is metered as TRANSCRIPTION_SECONDS with its cost.
    """

    def __init__(
        self,
        message_media_repo: MessageMediaRepoContract,
        media_storage: MediaStorageAdapterContract,
        voice_transcriber: VoiceTranscriberContract,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        usage_event_repo: UsageEventRepoContract,
        media_settings: MediaSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._message_media_repo: MessageMediaRepoContract = message_media_repo
        self._media_storage: MediaStorageAdapterContract = media_storage
        self._voice_transcriber: VoiceTranscriberContract = voice_transcriber
        self._business_repo: BusinessRepoContract = business_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._media_settings: MediaSettings = media_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: VoiceNoteTranscriptionRequest) -> VoiceNoteTranscription:
        attachment: MessageAttachment = input_data.attachment
        media: MessageMediaDocument | None = (
            None
            if attachment.media_id is None
            else self._message_media_repo.get(
                input_data.business_id, attachment.media_id
            )
        )
        if (
            attachment.kind is not AttachmentKind.AUDIO
            or attachment.problem is not None
            or media is None
        ):
            return VoiceNoteTranscription(attachment=attachment)

        if media.transcript is not None:
            return given(attachment, transcript=media.transcript)

        if (
            media.duration_seconds is not None
            and media.duration_seconds > self._media_settings.max_voice_seconds
        ):
            return given(attachment, problem=AttachmentProblem.TOO_LONG)

        audio: StoredMediaFile | None = self._media_storage.read(
            MediaLocation(business_id=media.business_id, path=media.storage_path)
        )
        if audio is None:
            return given(attachment, problem=AttachmentProblem.UNAVAILABLE)

        try:
            result: VoiceTranscriptionResult = self._voice_transcriber.transcribe(
                VoiceTranscriptionInput(
                    audio=audio,
                    model_id=self._media_settings.transcription_model_id,
                    **read_language_hints(
                        self._business_repo,
                        self._assistant_version_repo,
                        media.business_id,
                    ),
                )
            )
        except TranscriptionNotConfiguredError as error:
            logger.warning("A voice note was not transcribed: %s", error)
            return given(attachment, problem=AttachmentProblem.NOT_UNDERSTOOD)
        except ExternalServiceError:
            if not input_data.is_final_attempt:
                raise

            logger.exception("A voice note could not be transcribed.")
            return given(attachment, problem=AttachmentProblem.NOT_UNDERSTOOD)

        return self._keep(media, attachment, result)

    def _keep(
        self,
        media: MessageMediaDocument,
        attachment: MessageAttachment,
        result: VoiceTranscriptionResult,
    ) -> VoiceNoteTranscription:
        text: str = str(result.text).strip()[:MAX_TRANSCRIPT_LENGTH]
        seconds: AudioDurationSeconds = (
            media.duration_seconds
            or result.billed_seconds
            or estimate_duration_seconds(media.byte_count)
        )
        now: Microseconds = self._wall_clock.now_unix()
        transcript: TranscribedVoiceText | None = (
            TranscribedVoiceText(text) if text else None
        )
        media.transcript = transcript
        media.duration_seconds = seconds
        media.updated_at = now
        self._message_media_repo.save(media)
        self._usage_event_repo.append(
            UsageEventDocument(
                business_id=media.business_id,
                kind=UsageKind.TRANSCRIPTION_SECONDS,
                quantity=UsageQuantity(max(1, int(seconds))),
                cost_micro_usd=transcription_cost(
                    self._media_settings.transcription_model_id, seconds
                ),
                occurred_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        if transcript is None:
            return given(
                attachment,
                problem=AttachmentProblem.NOT_UNDERSTOOD,
                duration_seconds=seconds,
            )

        return given(attachment, transcript=transcript, duration_seconds=seconds)


def given(
    attachment: MessageAttachment,
    transcript: TranscribedVoiceText | None = None,
    problem: AttachmentProblem | None = None,
    duration_seconds: AudioDurationSeconds | None = None,
) -> VoiceNoteTranscription:
    return VoiceNoteTranscription(
        attachment=attachment.model_copy(
            update={
                "transcript": transcript,
                "problem": problem,
                "duration_seconds": duration_seconds or attachment.duration_seconds,
            }
        )
    )
