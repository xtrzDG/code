"""
What an Instagram message refers to that the assistant cannot see: a reply
to the business's story (`message.reply_to.story`) or a mention of the
business in the customer's own story (an attachment of type
`story_mention`, which is no file to read).
"""

from app.schemas.constants.channels import InboundContextNote
from app.utilities.channels.json_values import (
    JsonObject,
    read_object,
    read_objects,
    read_text,
)

STORY_MENTION_TYPE: str = "story_mention"


def read_story_note(message: JsonObject) -> InboundContextNote | None:
    reply_to: JsonObject = read_object(message, "reply_to") or {}
    if read_object(reply_to, "story") is not None:
        return InboundContextNote.STORY_REPLY

    if any(
        read_text(item, "type") == STORY_MENTION_TYPE
        for item in read_objects(message, "attachments")
    ):
        return InboundContextNote.STORY_MENTION

    return None


def is_story_mention(item: JsonObject) -> bool:
    return read_text(item, "type") == STORY_MENTION_TYPE
