from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ManagerTelegramLinkId
from app.schemas.typings.channels.strings import ManagerLinkCodeHash
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class ManagerTelegramLinkDocument(BaseDocument):
    """
    Pending link of a staff member's Telegram chat to a business.

    The owner creates it in the cabinet; the staff member sends
    "/start <code>" to the platform bot, which stores the chat id as a
    manager contact. Only the code hash is stored; a code works once and
    until `expires_at`.
    """

    id: ManagerTelegramLinkId = Field(default_factory=ManagerTelegramLinkId)
    business_id: BusinessId
    code_hash: ManagerLinkCodeHash
    manager_name: ManagerName
    language: LanguageTag
    created_by: UserId
    expires_at: Microseconds
    used_at: Microseconds | None = None
    linked_chat_id: ManagerContactAddress | None = None
