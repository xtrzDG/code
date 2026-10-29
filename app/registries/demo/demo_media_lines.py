"""
Demo customer messages that are not only text, as the worker leaves them:
a voice note with its transcript, a photo, a shared place, and a sticker the
assistant could not read.

    customer_voice("Hi, is there a table for four tonight?", seconds=6),
    customer_photo("Is this dish on your menu?"),
    customer_place(41.6938, 44.8015, "Freedom Square"),

The recorder stores the voice note's and the photo's file like the worker
does (`record_line_media`), so the cabinet plays and shows them.
"""

from uuid import uuid5

from typed_time_provider import Microseconds

from app.registries.demo.demo_lines import CUSTOMER_PAUSE_SECONDS
from app.registries.demo.demo_media_files import (
    build_demo_dish_photo,
    build_demo_voice_note,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.media import AttachmentKind, AttachmentProblem
from app.schemas.domain.message_media import (
    MessageAttachment,
    MessageMediaDocument,
    SharedLocation,
)
from app.schemas.dto.demo_data import DemoAttachmentLine, DemoMediaFile, DemoMessageLine
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.demo.constrained_integers import DemoReplyPauseSeconds
from app.schemas.typings.media.constrained_floats import Latitude, Longitude
from app.schemas.typings.media.constrained_integers import (
    AudioDurationSeconds,
    MediaByteCount,
)
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import MessageMediaId
from app.schemas.typings.media.strings import (
    LocationAddress,
    LocationName,
    TranscribedVoiceText,
)
from app.utilities.media.media_paths import (
    MESSAGE_MEDIA_NAMESPACE,
    media_storage_path,
)

VOICE_MEDIA_TYPE: str = "audio/wav"
PHOTO_MEDIA_TYPE: str = "image/png"


def customer_voice(
    transcript: str, seconds: int, pause: int = CUSTOMER_PAUSE_SECONDS
) -> DemoMessageLine:
    """A voice note the worker transcribed (no typed text)."""

    return customer_with(
        "",
        DemoAttachmentLine(
            attachment=MessageAttachment(
                kind=AttachmentKind.AUDIO,
                media_type=MessageMediaType(VOICE_MEDIA_TYPE),
                duration_seconds=AudioDurationSeconds(seconds),
                transcript=TranscribedVoiceText(transcript),
            ),
            content=build_demo_voice_note(seconds),
        ),
        pause,
    )


def customer_photo(
    caption: str, pause: int = CUSTOMER_PAUSE_SECONDS
) -> DemoMessageLine:
    """A photo with its caption (the caption is the message's text)."""

    return customer_with(
        caption,
        DemoAttachmentLine(
            attachment=MessageAttachment(
                kind=AttachmentKind.IMAGE,
                media_type=MessageMediaType(PHOTO_MEDIA_TYPE),
            ),
            content=build_demo_dish_photo(),
        ),
        pause,
    )


def customer_place(
    latitude: float,
    longitude: float,
    name: str,
    address: str | None = None,
    pause: int = CUSTOMER_PAUSE_SECONDS,
) -> DemoMessageLine:
    """A place the customer shared."""

    return customer_with(
        "",
        DemoAttachmentLine(
            attachment=MessageAttachment(
                kind=AttachmentKind.LOCATION,
                location=SharedLocation(
                    latitude=Latitude(latitude),
                    longitude=Longitude(longitude),
                    name=LocationName(name),
                    address=None if address is None else LocationAddress(address),
                ),
            )
        ),
        pause,
    )


def customer_sticker(pause: int = CUSTOMER_PAUSE_SECONDS) -> DemoMessageLine:
    """A sticker: the assistant asked the customer to write instead."""

    return customer_with(
        "",
        DemoAttachmentLine(
            attachment=MessageAttachment(
                kind=AttachmentKind.STICKER,
                problem=AttachmentProblem.UNSUPPORTED_KIND,
            )
        ),
        pause,
    )


def customer_with(
    text: str, attachment: DemoAttachmentLine, pause: int
) -> DemoMessageLine:
    return DemoMessageLine(
        author=MessageAuthor.CUSTOMER,
        text=MessageText(text),
        attachments=[attachment],
        pause_seconds=DemoReplyPauseSeconds(pause),
    )


def record_line_media(
    business_id: BusinessId,
    message_id: MessageId,
    line: DemoMessageLine,
    moment: Microseconds,
) -> tuple[list[MessageAttachment], list[DemoMediaFile]]:
    """
    The message's attachments, each voice note and photo with its stored
    file, and the files to store.
    """

    attachments: list[MessageAttachment] = []
    files: list[DemoMediaFile] = []
    for position, item in enumerate(line.attachments):
        attachment: MessageAttachment = item.attachment
        if item.content is None or attachment.media_type is None:
            attachments.append(attachment)
            continue

        media_id = MessageMediaId(
            uuid5(MESSAGE_MEDIA_NAMESPACE, f"demo|{message_id}|{position}")
        )
        path = media_storage_path(business_id, media_id, attachment.media_type)
        byte_count = MediaByteCount(len(item.content))
        attachments.append(
            attachment.model_copy(
                update={
                    "media_id": media_id,
                    "storage_path": path,
                    "byte_count": byte_count,
                }
            )
        )
        media = MessageMediaDocument(
            id=media_id,
            business_id=business_id,
            message_id=message_id,
            kind=attachment.kind,
            storage_path=path,
            media_type=attachment.media_type,
            byte_count=byte_count,
            duration_seconds=attachment.duration_seconds,
            transcript=attachment.transcript,
            created_at=moment,
            updated_at=moment,
        )
        files.append(DemoMediaFile(media=media, content=item.content))

    return attachments, files
