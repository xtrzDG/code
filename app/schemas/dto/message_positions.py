"""Where a message stands in its chat, without the message itself."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.typings.conversations.prefixed_id import MessageId


class MessagePosition(ImmutableDTO):
    """
    A message's id and creation time, as the indexed columns hold them: a
    widget poll orders the newest messages and finds its cursor among them
    without reading them, then reads only the messages after the cursor.
    """

    id: MessageId
    created_at: Microseconds
