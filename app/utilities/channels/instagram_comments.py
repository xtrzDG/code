"""
Reading the comments of Meta's Instagram webhook (`object: instagram`,
`entry[].changes[]` of the field `comments`), signed like its messages.
"""

from app.schemas.dto.channels.comment_replies import InstagramComment
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.meta_connection.constrained_strings import MetaCommentId
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_identifier,
    read_object,
    read_objects,
    read_text,
)

INSTAGRAM_OBJECT: str = "instagram"
COMMENTS_FIELD: str = "comments"


def read_instagram_comments(body: bytes) -> list[InstagramComment]:
    """
    The new comments of a webhook, in order. The account's own comments
    (its replies under its posts) and comments without words, author or a
    valid id are left out.
    """

    root: JsonObject | None = parse_json_object(body)
    if root is None or read_text(root, "object") != INSTAGRAM_OBJECT:
        return []

    comments: list[InstagramComment] = []
    for entry in read_objects(root, "entry"):
        account_id: str | None = read_identifier(entry, "id")
        if account_id is None:
            continue

        for change in read_objects(entry, "changes"):
            if read_text(change, "field") != COMMENTS_FIELD:
                continue

            comment: InstagramComment | None = read_comment(
                account_id, read_object(change, "value") or {}
            )
            if comment is not None:
                comments.append(comment)

    return comments


def read_comment(account_id: str, value: JsonObject) -> InstagramComment | None:
    author: JsonObject = read_object(value, "from") or {}
    author_id: str | None = read_identifier(author, "id")
    raw_comment_id: str | None = read_identifier(value, "id")
    text: str | None = read_text(value, "text")
    if (
        author_id is None
        or author_id == account_id
        or raw_comment_id is None
        or text is None
    ):
        return None

    try:
        comment_id = MetaCommentId(raw_comment_id)
    except ValueError:
        return None

    username: str | None = read_text(author, "username")
    return InstagramComment(
        account_id=ChannelExternalId(account_id),
        comment_id=comment_id,
        author_id=ChannelUserId(author_id),
        author_username=None if username is None else ContactName(username),
        text=MessageText(text),
    )
