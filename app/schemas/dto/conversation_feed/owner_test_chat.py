"""Owner cabinet: the owner's test chat with an assistant version."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_strings import (
    OwnerTestChatSessionKey,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.users.prefixed_id import UserId


class OwnerTestChatRequest(ImmutableDTO):
    """
    HTTP body of the owner's test chat.

    Without `assistant_version_id` the published version answers, or the
    newest ready (then draft) version before the first publication.
    `session_key` keeps parallel test chats apart.
    """

    text: MessageText
    session_key: OwnerTestChatSessionKey | None = None
    assistant_version_id: AssistantVersionId | None = None


class OwnerTestChatCommand(ImmutableDTO):
    """A signed-in owner or staff member writes to the assistant from the cabinet."""

    user_id: UserId
    business_id: BusinessId
    request: OwnerTestChatRequest


class OwnerTestChatVersionQuery(ImmutableDTO):
    """
    Which assistant version answers a test chat message: the requested one,
    else the published one, else the newest ready (then draft) version.
    """

    business_id: BusinessId
    requested_version_id: AssistantVersionId | None = None
    published_version_id: AssistantVersionId | None = None
