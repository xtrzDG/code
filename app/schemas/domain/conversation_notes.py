from base_pydantic_schemas import BaseDocument
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.inbox.constrained_strings import ConversationNoteText
from app.schemas.typings.inbox.prefixed_id import ConversationNoteId
from app.schemas.typings.users.prefixed_id import UserId


class ConversationNoteDocument(BaseDocument):
    """
    An internal note of the team on one conversation ("called back, prefers
    Saturday"). Only owners and staff of the business read it: it is kept
    apart from the messages, so it never reaches the customer, the language
    model or the customer's widget. Reading, writing and deleting notes are
    audited; erasing the customer's data deletes the notes of their
    conversations.
    """

    id: ConversationNoteId = Field(default_factory=ConversationNoteId)
    business_id: BusinessId
    conversation_id: ConversationId
    author_user_id: UserId
    text: ConversationNoteText
