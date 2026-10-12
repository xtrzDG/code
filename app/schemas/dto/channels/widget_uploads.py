"""Photos and voice notes a website chat visitor uploads before sending them."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.dto.conversations import InboundMessage
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetSessionKey
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.media.constrained_integers import (
    AudioDurationSeconds,
    MediaByteCount,
    MediaByteLimit,
    VoiceDurationLimitSeconds,
)
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import WidgetUploadId
from app.schemas.typings.media.strings import DeclaredUploadType


class WidgetUploadAdmission(ImmutableDTO):
    """
    A website visitor starts an upload (the visitor key from the
    X-Widget-Session-Key header): counted and checked before a byte of the
    file is read.
    """

    business_id: BusinessId
    session_key: WidgetSessionKey
    client_ip_address: ClientIpAddress | None = None


class WidgetUploadAllowance(ImmutableDTO):
    """
    The upload may go on: the largest file it may carry (the larger of the
    photo and voice note caps), so the route reads no more than that.
    """

    max_file_bytes: MediaByteLimit


class WidgetUploadCommand(ImmutableDTO):
    """
    The file of an admitted upload, as the browser sent it: its bytes and
    the type it declared for them (never trusted on its own).
    """

    business_id: BusinessId
    session_key: WidgetSessionKey
    content: bytes = Field(repr=False)
    declared_type: DeclaredUploadType | None = None


class WidgetAttachmentView(ImmutableDTO):
    """
    An uploaded file the visitor's next message may name (`attachment_id`):
    what it is, its type as its bytes say, its size and, for a voice note,
    its length.
    """

    attachment_id: WidgetUploadId
    kind: AttachmentKind
    media_type: MessageMediaType
    byte_count: MediaByteCount
    duration_seconds: AudioDurationSeconds | None = None


class WidgetAttachmentRulesView(ImmutableDTO):
    """
    What the widget lets a visitor send besides text: photos of these types
    up to `max_image_bytes` (MEDIA_MAX_IMAGE_BYTES), voice notes of these
    types up to `max_voice_seconds` (MEDIA_MAX_VOICE_SECONDS) and
    `max_voice_bytes` (MEDIA_MAX_VOICE_BYTES). The API checks all of it
    again.
    """

    image_types: list[MessageMediaType]
    audio_types: list[MessageMediaType]
    max_image_bytes: MediaByteLimit
    max_voice_bytes: MediaByteLimit
    max_voice_seconds: VoiceDurationLimitSeconds


class AcceptedWidgetMessage(ImmutableDTO):
    """
    A visitor message accepted for the inbox, with the uploads it names
    (checked: the visitor's own, not attached yet, not expired) and what
    the inbox keeps of them; queueing claims each upload once.
    """

    message: InboundMessage
    upload_ids: list[WidgetUploadId] = Field(default_factory=list[WidgetUploadId])
    attachments: list[InboundAttachment] = Field(
        default_factory=list[InboundAttachment]
    )
