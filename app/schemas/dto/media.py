"""
Customer files besides text: where they are kept, how they are fetched from
a messaging platform and transcribed, and how the cabinet shows them.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.media import AttachmentKind, AttachmentProblem
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.message_media import SharedLocation
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.media.booleans import IsFinalInboxAttempt, IsMediaDeleted
from app.schemas.typings.media.constrained_integers import (
    AudioDurationSeconds,
    DeletedMediaCount,
    MediaByteCount,
    MediaByteLimit,
)
from app.schemas.typings.media.constrained_strings import (
    MessageMediaType,
    TranscriptionModelId,
)
from app.schemas.typings.media.prefixed_id import MessageMediaId
from app.schemas.typings.media.strings import (
    MapLinkUrl,
    MediaStoragePath,
    ProviderMediaId,
    ProviderMediaType,
    TranscribedVoiceText,
)
from app.schemas.typings.users.prefixed_id import UserId


class MediaLocation(ImmutableDTO):
    """
    Where a customer file is kept: its path in the media storage and the
    business it belongs to (the business's own key encrypts it).
    """

    business_id: BusinessId
    path: MediaStoragePath


class StoredMediaFile(ImmutableDTO):
    """A customer file as stored: its bytes and recognized media type."""

    content: bytes = Field(repr=False)
    media_type: MessageMediaType


class ChannelMediaRequest(ImmutableDTO):
    """
    One file to download from a messaging platform, at most `max_bytes`
    long. `credential` is the channel's decrypted bot or page token (None
    for WhatsApp, which uses the platform token); never in logs.
    """

    channel: ChannelKind
    provider_media_id: ProviderMediaId
    credential: ChannelSecret | None = Field(default=None, repr=False)
    max_bytes: MediaByteLimit


class FetchedMedia(ImmutableDTO):
    """A downloaded file and the media type the platform declared for it."""

    content: bytes = Field(repr=False)
    declared_type: ProviderMediaType | None = None


class VoiceTranscriptionInput(ImmutableDTO):
    """
    A voice note to transcribe: the audio, the languages it is likely in
    (the assistant's languages, the default first) and words that help the
    recognizer (the business's name).
    """

    audio: StoredMediaFile
    model_id: TranscriptionModelId
    language_hints: list[LanguageTag] = Field(default_factory=list[LanguageTag])
    keywords: list[BusinessName] = Field(default_factory=list[BusinessName])


class VoiceTranscriptionResult(ImmutableDTO):
    """
    What the recognizer heard (empty: no speech) and, when it said so, the
    length of the audio it was billed for.
    """

    text: TranscribedVoiceText
    billed_seconds: AudioDurationSeconds | None = None


class VoiceNoteTranscriptionRequest(ImmutableDTO):
    """
    Transcribe one stored voice note of a business (or return the
    transcript a previous attempt kept). `duration_seconds` is the length
    the platform reported, when it did.
    """

    business_id: BusinessId
    media_id: MessageMediaId
    duration_seconds: AudioDurationSeconds | None = None


class VoiceNoteTranscription(ImmutableDTO):
    """
    A transcribed voice note: its text (None when nothing could be heard or
    the service failed) and length.
    """

    transcript: TranscribedVoiceText | None = None
    duration_seconds: AudioDurationSeconds | None = None


class InboundMediaRequest(ImmutableDTO):
    """
    The files of one claimed inbox event to download and store; on the
    job's last attempt a file the platform does not hand out is given up
    (the customer is asked to write) instead of failing the job.
    """

    event: InboundEventDocument
    is_final_attempt: IsFinalInboxAttempt = False


class LlmImageInput(ImmutableDTO):
    """A stored photo the model is shown in a user turn."""

    location: MediaLocation
    media_type: MessageMediaType


class MessageMediaQuery(ImmutableDTO):
    """An owner or staff member opens a file a customer sent (audited)."""

    user_id: UserId
    business_id: BusinessId
    media_id: MessageMediaId
    client_ip_address: ClientIpAddress | None = None


class MessageAttachmentView(ImmutableDTO):
    """
    An attachment of a customer message in the cabinet's transcript: a voice
    note to play (`media_id`) with its transcript, a photo (`media_id`), a
    place with a map link, or what the assistant could not read (`problem`).
    `is_media_deleted`: the retention purge removed the file.
    """

    kind: AttachmentKind
    media_id: MessageMediaId | None = None
    media_type: MessageMediaType | None = None
    byte_count: MediaByteCount | None = None
    duration_seconds: AudioDurationSeconds | None = None
    transcript: TranscribedVoiceText | None = None
    location: SharedLocation | None = None
    map_url: MapLinkUrl | None = None
    problem: AttachmentProblem | None = None
    is_media_deleted: IsMediaDeleted = False


class MessageMediaPurgeResult(ImmutableDTO):
    """Customer files removed by one retention purge run."""

    deleted_files: DeletedMediaCount
