from typing import Self

from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field, model_validator
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.booleans import IsContactBlocked, IsVipCustomer
from app.schemas.typings.contacts.constrained_strings import (
    CustomerTag,
    CustomerTagKey,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName, FoldedContactName
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId


class ChannelIdentity(PersistentDocument):
    """How a contact is addressed in one channel."""

    channel: ChannelKind
    channel_user_id: ChannelUserId


class ContactTagMark(PersistentDocument):
    """
    A tag on a customer: which (as written, and its case-folded `key` the
    filters match), when and by whom (None: the platform).
    """

    tag: CustomerTag
    key: CustomerTagKey
    added_at: Microseconds
    added_by: UserId | None = None


class ContactBlock(PersistentDocument):
    """Why the assistant no longer answers a customer: who blocked them, when."""

    blocked_at: Microseconds
    blocked_by: UserId


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

    Version 4 adds the team's customer card (1140), all optional: `tags`
    (indexed by `tags[].key`), the `is_vip` flag and `block`, set while the
    assistant must not answer the customer (`is_blocked` mirrors it for the
    list's filter). Only the card writes of the repository change them; a
    plain save keeps them as stored, so a turn that read the contact
    earlier never undoes a tag or a block. An erased customer has none.
    """

    schema_version: SchemaVersion = SchemaVersion("4")
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
    tags: list[ContactTagMark] = Field(default_factory=list[ContactTagMark])
    is_vip: IsVipCustomer = False
    block: ContactBlock | None = None
    is_blocked: IsContactBlocked = False

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

    @model_validator(mode="after")
    def mirror_block(self) -> Self:
        """`is_blocked` (the list's filter) follows `block`."""

        is_blocked: bool = self.block is not None
        if self.is_blocked != is_blocked:
            self.is_blocked = is_blocked

        return self
