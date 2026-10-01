from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)


class ChannelIdentity(PersistentDocument):
    """How a contact is addressed in one channel."""

    channel: ChannelKind
    channel_user_id: ChannelUserId


class ContactDocument(BaseDocument):
    """A customer of one business (concept table `contacts`)."""

    id: ContactId = Field(default_factory=ContactId)
    business_id: BusinessId
    name: ContactName | None = None
    phone_number: E164PhoneNumber | None = None
    language: LanguageTag | None = None
    channel_identities: list[ChannelIdentity] = Field(
        default_factory=list[ChannelIdentity]
    )
