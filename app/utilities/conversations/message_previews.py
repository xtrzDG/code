"""The beginning of a message for a list row."""

from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.conversations import MessageDocument
from app.schemas.typings.conversations.strings import MessagePreview, MessageText
from app.utilities.media.attachment_texts import readable_message_text

PREVIEW_LENGTH: int = 160
ELLIPSIS: str = "…"


def build_message_preview(text: MessageText) -> MessagePreview:
    """
    The message on one line, cut at the last space before PREVIEW_LENGTH
    characters (or at the limit inside a long word) with an ellipsis.
    """

    one_line: str = " ".join(str(text).split())
    if len(one_line) <= PREVIEW_LENGTH:
        return MessagePreview(one_line)

    cut: str = one_line[:PREVIEW_LENGTH]
    last_space: int = cut.rfind(" ")
    if last_space > PREVIEW_LENGTH // 2:
        cut = cut[:last_space]

    return MessagePreview(cut.rstrip() + ELLIPSIS)


def build_written_message_preview(message: MessageDocument) -> MessagePreview:
    """
    The preview of a stored message: what was written, a voice note's
    transcript and a shared place included (a photo alone has none; the
    attachment's kind tells it).
    """

    return build_message_preview(
        MessageText(readable_message_text(str(message.text), message.attachments))
    )


def first_attachment_kind(message: MessageDocument) -> AttachmentKind | None:
    """What the message carries besides text, for an icon next to the preview."""

    return message.attachments[0].kind if message.attachments else None
