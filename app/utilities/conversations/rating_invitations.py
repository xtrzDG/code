"""Which answers the website chat asks the visitor to rate right away."""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.typings.channels.booleans import InvitesRating

# A turn that did one of these for the visitor is worth a thumbs up or down.
RATED_OUTCOMES: frozenset[AssistantToolName] = frozenset(
    {AssistantToolName.CREATE_BOOKING, AssistantToolName.CREATE_LEAD}
)


def invites_rating(message: MessageDocument) -> InvitesRating:
    """
    An assistant answer of a turn that created a booking or took a lead (a
    tool call that did not fail): the widget shows its thumbs under it.
    """

    return message.author is MessageAuthor.ASSISTANT and any(
        call.tool_name in RATED_OUTCOMES and not call.is_error
        for call in message.tool_calls
    )
