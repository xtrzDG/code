"""The beginning of a message for a list row."""

from app.schemas.typings.conversations.strings import MessagePreview, MessageText

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
