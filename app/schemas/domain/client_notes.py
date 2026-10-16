from base_pydantic_schemas import BaseDocument
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.booleans import IsClientNotePinned
from app.schemas.typings.client_health.constrained_strings import ClientNoteText
from app.schemas.typings.client_health.prefixed_id import ClientNoteId
from app.schemas.typings.users.prefixed_id import UserId


class ClientNoteDocument(BaseDocument):
    """
    A platform admin's note about a client (`client_notes`, migration
    1143): a call, a promise, the state of a deal. The platform team reads
    it on the admin client page, pinned notes first; the client's own team
    never sees it, and it never reaches the assistant.
    """

    id: ClientNoteId = Field(default_factory=ClientNoteId)
    business_id: BusinessId
    author_user_id: UserId
    text: ClientNoteText
    is_pinned: IsClientNotePinned = False
