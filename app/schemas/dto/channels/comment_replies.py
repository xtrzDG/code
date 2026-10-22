"""Instagram comment-to-DM: the owner's settings and the comments it answers."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.meta_connection.booleans import IsCommentReplyOn
from app.schemas.typings.meta_connection.constrained_strings import (
    CommentReplyText,
    CommentTriggerKeyword,
    MetaCommentId,
)
from app.schemas.typings.users.prefixed_id import UserId

MAX_COMMENT_TRIGGER_KEYWORDS: int = 20


class InstagramCommentRepliesRequest(ImmutableDTO):
    """
    HTTP body of the Instagram card's comment-to-DM: on or off, the
    keywords a comment must hold (up to 20; letter case does not matter)
    and the private reply it gets. Turning it on needs a keyword and a
    text; turning it off keeps them for later.
    """

    is_on: IsCommentReplyOn
    keywords: list[CommentTriggerKeyword] = Field(
        default_factory=list[CommentTriggerKeyword],
        max_length=MAX_COMMENT_TRIGGER_KEYWORDS,
    )
    reply_text: CommentReplyText | None = None


class SetInstagramCommentRepliesCommand(ImmutableDTO):
    """The owner changes the Instagram account's comment-to-DM."""

    user_id: UserId
    business_id: BusinessId
    request: InstagramCommentRepliesRequest
    client_ip_address: ClientIpAddress | None = None


class InstagramCommentRepliesView(ImmutableDTO):
    """The Instagram account's comment-to-DM as the cabinet shows it."""

    is_on: IsCommentReplyOn
    keywords: list[CommentTriggerKeyword] = Field(
        default_factory=list[CommentTriggerKeyword]
    )
    reply_text: CommentReplyText | None = None


class InstagramComment(ImmutableDTO):
    """
    A new comment under an Instagram account's post, as Meta's `comments`
    webhook tells it: the account it was written to, the comment and its
    author (their Instagram-scoped id and username), and its words.
    """

    account_id: ChannelExternalId
    comment_id: MetaCommentId
    author_id: ChannelUserId
    author_username: ContactName | None = None
    text: MessageText = Field(repr=False)
