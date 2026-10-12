"""What the widget tells a visitor about the files it may send."""

from app.schemas.configurations.media_settings import MediaSettings
from app.schemas.dto.channels.widget_uploads import WidgetAttachmentRulesView
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.utilities.media.upload_checks import UPLOAD_AUDIO_TYPES, UPLOAD_IMAGE_TYPES


def widget_attachment_rules(media: MediaSettings) -> WidgetAttachmentRulesView:
    """The photo and voice note types and caps the upload route enforces."""

    return WidgetAttachmentRulesView(
        image_types=[MessageMediaType(kind) for kind in UPLOAD_IMAGE_TYPES],
        audio_types=[MessageMediaType(kind) for kind in UPLOAD_AUDIO_TYPES],
        max_image_bytes=media.max_image_bytes,
        max_voice_bytes=media.max_voice_bytes,
        max_voice_seconds=media.max_voice_seconds,
    )
