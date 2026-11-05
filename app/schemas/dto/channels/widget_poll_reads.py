"""What one website-widget poll reads (`WidgetPollReadAdapterContract`)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.message_positions import MessagePosition
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl


class WidgetPollRead(ImmutableDTO):
    """
    Everything a widget poll answers from, read at once.

    `allowed_origins`: the websites the business allows to show its chat
    (empty: any). `conversations`: the visitor's web-chat conversations
    without the sandbox ones, the current one (last written to) first.
    `newest`: where the newest messages of those conversations stand (at
    most the window asked for, newest first); None when they could not be
    read with the conversations (the poll then reads the whole chat).
    `after_cursor`: those of `newest` that come after the poll's cursor in
    answer order, in full (none when the cursor is not among them).
    """

    allowed_origins: list[PublicBaseUrl] = Field(default_factory=list[PublicBaseUrl])
    conversations: list[ConversationDocument] = Field(
        default_factory=list[ConversationDocument]
    )
    newest: list[MessagePosition] | None = None
    after_cursor: list[MessageDocument] = Field(default_factory=list[MessageDocument])
