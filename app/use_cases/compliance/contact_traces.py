"""
The traces of a visitor outside their conversations: missed calls from
their numbers, messages queued to their accounts, webhook events they sent
requests for feedback after their visits, their places on the waitlist
and the rebooking campaign's messages to them. Every read is an indexed
lookup of the visitor's own numbers, accounts, conversations or contact.
"""

from dataclasses import dataclass

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.call_follow_up_repositories import (
    MissedCallRepoContract,
)
from app.contracts.repositories.campaign_repositories import (
    CampaignMessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    InboundEventRepoContract,
    OutboundMessageRepoContract,
)
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.campaigns import CampaignMessageDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.deliveries.constrained_strings import OutboundRecipientKey
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.deliveries.delivery_keys import customer_recipient_key


@dataclass(frozen=True)
class ContactTraces:
    missed_calls: list[MissedCallDocument]
    outbound_messages: list[OutboundMessageDocument]
    inbound_events: list[InboundEventDocument]
    feedback_requests: list[FeedbackRequestDocument]
    waitlist_entries: list[WaitlistEntryDocument]
    campaign_messages: list[CampaignMessageDocument]


@dataclass(frozen=True)
class ContactTraceReader:
    channel_repo: ChannelRepoContract
    missed_call_repo: MissedCallRepoContract
    outbound_message_repo: OutboundMessageRepoContract
    inbound_event_repo: InboundEventRepoContract
    feedback_request_repo: FeedbackRequestRepoContract
    waitlist_entry_repo: WaitlistEntryRepoContract | None = None
    campaign_message_repo: CampaignMessageRepoContract | None = None

    def read(
        self,
        contact: ContactDocument,
        conversations: list[ConversationDocument],
    ) -> ContactTraces:
        accounts: dict[ChannelUserId, ChannelKind] = {
            identity.channel_user_id: identity.channel
            for identity in contact.channel_identities
        }
        for conversation in conversations:
            accounts.setdefault(conversation.channel_user_id, conversation.channel)

        return ContactTraces(
            missed_calls=[
                missed_call
                for phone in contact_phones(contact)
                for missed_call in self.missed_call_repo.list_by_caller(
                    contact.business_id, phone
                )
            ],
            outbound_messages=[
                message
                for key in self._recipient_keys(contact, accounts)
                for message in self.outbound_message_repo.list_for_recipient(
                    contact.business_id, key
                )
            ],
            inbound_events=self.inbound_event_repo.list_by_customer(
                contact.business_id,
                list(accounts),
                [conversation.id for conversation in conversations],
            ),
            feedback_requests=self.feedback_request_repo.list_by_contact(
                contact.business_id, contact.id
            ),
            waitlist_entries=(
                []
                if self.waitlist_entry_repo is None
                else self.waitlist_entry_repo.list_of_contact(
                    contact.business_id, contact.id
                )
            ),
            campaign_messages=(
                []
                if self.campaign_message_repo is None
                else self.campaign_message_repo.list_of_contact(
                    contact.business_id, contact.id
                )
            ),
        )

    def _recipient_keys(
        self,
        contact: ContactDocument,
        accounts: dict[ChannelUserId, ChannelKind],
    ) -> list[OutboundRecipientKey]:
        """The visitor's outbox recipients in every channel of the business."""

        channels: list[ChannelDocument] = self.channel_repo.list_by_business(
            contact.business_id
        )
        return list(
            dict.fromkeys(
                customer_recipient_key(channel.id, account)
                for account, kind in accounts.items()
                for channel in channels
                if channel.kind is kind
            )
        )


def contact_phones(contact: ContactDocument) -> list[E164PhoneNumber]:
    """Every number of the visitor: typed, proven, and their WhatsApp number."""

    phones: list[E164PhoneNumber] = [
        phone
        for phone in (contact.verified_phone_number, contact.phone_number)
        if phone is not None
    ]
    for identity in contact.channel_identities:
        if identity.channel is ChannelKind.WHATSAPP:
            try:
                phones.append(E164PhoneNumber(f"+{identity.channel_user_id}"))
            except ValueError:
                continue

    return list(dict.fromkeys(phones))
