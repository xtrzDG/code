from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

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
    """
    A customer of one business (concept table `contacts`).

    `phone_number` may come from what the customer typed (the model passes
    it to booking and lead tools); `verified_phone_number` only ever comes
    from a channel that proves it (WhatsApp sender, a contact the Telegram
    user shared about themselves, the caller ID of a call). Only the
    verified phone proves that bookings under that phone are the
    customer's own.

    `erased_at` marks a customer erased at their request: the document then
    keeps no personal data (no name, phones, language or channel
    identities), only its id, so records that point to it read as erased.

    `opted_out_channels`: channels the customer asked to get no messages in
    that they did not ask for (reminders, text-backs after a missed call);
    PHONE covers SMS to their number. Version 2 adds it (optional).
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    id: ContactId = Field(default_factory=ContactId)
    business_id: BusinessId
    name: ContactName | None = None
    phone_number: E164PhoneNumber | None = None
    verified_phone_number: E164PhoneNumber | None = None
    language: LanguageTag | None = None
    channel_identities: list[ChannelIdentity] = Field(
        default_factory=list[ChannelIdentity]
    )
    erased_at: Microseconds | None = None
    opted_out_channels: list[ChannelKind] = Field(default_factory=list[ChannelKind])
