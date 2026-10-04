"""Message attachments built from what the worker stored or gave up."""

from app.schemas.constants.media import AttachmentProblem
from app.schemas.domain.message_media import (
    InboundAttachment,
    MessageAttachment,
    MessageMediaDocument,
)


def attachment_of_stored_media(media: MessageMediaDocument) -> MessageAttachment:
    """A stored voice note or photo, with the transcript kept so far."""

    return MessageAttachment(
        kind=media.kind,
        media_id=media.id,
        storage_path=media.storage_path,
        media_type=media.media_type,
        byte_count=media.byte_count,
        duration_seconds=media.duration_seconds,
        transcript=media.transcript,
    )


def unreadable_attachment(
    attachment: InboundAttachment, problem: AttachmentProblem
) -> MessageAttachment:
    """An attachment the assistant cannot read, and why."""

    return MessageAttachment(
        kind=attachment.kind,
        duration_seconds=attachment.duration_seconds,
        byte_count=attachment.declared_bytes,
        problem=problem,
    )
