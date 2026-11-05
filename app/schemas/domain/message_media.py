"""
What customers send besides text: the attachments of a message as the
channel delivered them, as the assistant read them, and the stored files.
"""

from base_pydantic_schemas import BaseDocument, PersistentDocument
from typed_time_provider import Microseconds

from app.schemas.constants.media import AttachmentKind, AttachmentProblem
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.media.constrained_floats import Latitude, Longitude
from app.schemas.typings.media.constrained_integers import (
    AudioDurationSeconds,
    MediaByteCount,
)
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import MessageMediaId
from app.schemas.typings.media.strings import (
    AttachmentCaption,
    LocationAddress,
    LocationName,
    MediaStoragePath,
    ProviderMediaId,
    ProviderMediaType,
    TranscribedVoiceText,
)


class SharedLocation(PersistentDocument):
    """A place a customer shared: its coordinates, name and address."""

    latitude: Latitude
    longitude: Longitude
    name: LocationName | None = None
    address: LocationAddress | None = None


class InboundAttachment(PersistentDocument):
    """
    One attachment of a customer message as the channel adapter read it from
    the webhook: what it is, where the platform keeps its file
    (`provider_media_id`, fetched by the worker), the type and size the
    platform declared, the caption and, for a location, the place. Telegram
    tells a voice note's length; other platforms do not.
    """

    kind: AttachmentKind
    provider_media_id: ProviderMediaId | None = None
    mime_type: ProviderMediaType | None = None
    caption: AttachmentCaption | None = None
    location: SharedLocation | None = None
    declared_bytes: MediaByteCount | None = None
    duration_seconds: AudioDurationSeconds | None = None


class MessageAttachment(PersistentDocument):
    """
    One attachment of a stored customer message, as the assistant read it.

    A voice note or photo the platform stored has `media_id` (its
    `MessageMediaDocument`) and `storage_path`; a voice note's text is
    `transcript`, a location its `location`. `problem` says why the
    assistant could not read it (the customer was asked to write instead);
    `media_deleted_at` is when the retention purge removed the file.
    """

    kind: AttachmentKind
    media_id: MessageMediaId | None = None
    storage_path: MediaStoragePath | None = None
    media_type: MessageMediaType | None = None
    byte_count: MediaByteCount | None = None
    duration_seconds: AudioDurationSeconds | None = None
    transcript: TranscribedVoiceText | None = None
    location: SharedLocation | None = None
    problem: AttachmentProblem | None = None
    media_deleted_at: Microseconds | None = None


class MessageMediaDocument(BaseDocument):
    """
    A file a customer sent (a voice note, a photo), kept encrypted in the
    business's media storage for `recording_retention_days`, like call
    recordings.

    The id is derived from the inbox event and the attachment's position,
    so a turn that runs again finds the file (and the transcript) it
    stored. `message_id` is the transcript message it belongs to; the
    retention purge marks the file deleted there.
    """

    id: MessageMediaId
    business_id: BusinessId
    message_id: MessageId
    kind: AttachmentKind
    storage_path: MediaStoragePath
    media_type: MessageMediaType
    byte_count: MediaByteCount
    duration_seconds: AudioDurationSeconds | None = None
    transcript: TranscribedVoiceText | None = None
