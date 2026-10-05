from typing import Self

from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field, model_validator
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName, FoldedContactName
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

    Version 3 adds the customer list's lookups (migration 1122):
    `last_seen_at`, the customer's latest activity (a message, a call, a
    missed call, a booking taken for them, the erasure), the list's order;
    a real customer has it from the moment they appear, while a contact
    made only by the owner's test chat or the autotests (OWNER_TEST
    identities only) never gets one and stays out of the list.
    `display_name_folded`, the name as the search compares it, is kept in
    step with `name` by the repository.
    """

    schema_version: SchemaVersion = SchemaVersion("3")
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
    last_seen_at: Microseconds | None = None
    display_name_folded: FoldedContactName | None = None

    @property
    def is_test_only(self) -> bool:
        """Made only by the owner's test chat or the autotests."""

        return self.channel_identities != [] and all(
            identity.channel is ChannelKind.OWNER_TEST
            for identity in self.channel_identities
        )

    @model_validator(mode="after")
    def start_seen_when_created(self) -> Self:
        """A real customer is seen from the moment the contact is created."""

        if self.last_seen_at is None and not self.is_test_only:
            self.last_seen_at = self.created_at

        return self
