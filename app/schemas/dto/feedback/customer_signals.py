"""What the platform answers itself: STOP, START and a visit rating."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.feedback import CustomerSignalKind
from app.schemas.dto.handoffs import HandoffCommand
from app.schemas.typings.conversations.strings import MessageText


class CustomerSignalReply(ImmutableDTO):
    """
    The platform's answer to a customer's signal instead of the
    assistant's: the text (None: stay silent, the customer is past the
    hourly message limit) and, for a low visit rating, the handoff to open
    (None when staff already own the conversation).
    """

    kind: CustomerSignalKind
    text: MessageText | None = None
    handoff: HandoffCommand | None = None
