"""Files website chat visitors upload before the message that carries them."""

from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.media import AttachmentKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import WidgetVisitorId
from app.schemas.typings.media.constrained_integers import (
    AudioDurationSeconds,
    MediaByteCount,
)
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import WidgetUploadId
from app.schemas.typings.media.strings import MediaStoragePath


class WidgetUploadDocument(BaseDocument):
    """
    A photo or voice note a website chat visitor uploaded, waiting for the
    message that names it (migration 1191).

    The file was checked when it came (its bytes are the type the browser
    declared, under the cap of its kind, a voice note's length read from
    its container, a photo's metadata removed) and is kept encrypted with
    the business's key in the media storage at `storage_path`. It belongs to
    the visitor who uploaded it (`visitor_id`, derived one-way from the
    widget's visitor key): only a message of that visitor can name it, once
    (`attached_at`). The worker then copies it into the message's own
    stored file, kept for the business's retention; the upload itself is
    purged a day after it came, attached or not.
    """

    id: WidgetUploadId = Field(default_factory=WidgetUploadId)
    business_id: BusinessId
    visitor_id: WidgetVisitorId
    kind: AttachmentKind
    media_type: MessageMediaType
    storage_path: MediaStoragePath
    byte_count: MediaByteCount
    duration_seconds: AudioDurationSeconds | None = None
    attached_at: Microseconds | None = None
