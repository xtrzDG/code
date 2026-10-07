"""
A message to a caller after the call (the booking's confirmation, the
links the phone assistant promised): queued in the outbox for the first
messenger that can carry it now, and sent by the worker with retries.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.storage import StorageUnitOfWorkContract
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
)
from app.schemas.typings.conversations.prefixed_id import CallId
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.shared.messaging_window import (
    WINDOWED_CHANNELS,
    is_messaging_window_open,
)
from app.use_cases.shared.outbox_queue import queue_outbound_message
from app.utilities.channels.caller_reachability import list_reachable_identities
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.deliveries.customer_message_keys import (
    call_message_idempotency_key,
)
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_outbound_message_id,
)


@dataclass(frozen=True)
class CallMessageOutbox:
    """
    Picks the caller's messenger and queues one message of a kind per call
    (a repeated webhook finds it queued). A messenger with a 24-hour window
    (WhatsApp, Messenger, Instagram) carries free text only when the caller
    wrote there within the last day; Telegram always can.
    """

    channel_repo: ChannelRepoContract
    conversation_repo: ConversationRepoContract
    message_repo: MessageRepoContract
    outbound_message_repo: OutboundMessageRepoContract
    job_queue: JobQueueFacilitatorContract
    unit_of_work: StorageUnitOfWorkContract | None
    wall_clock: WallClock[Microseconds]

    def queue(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        call_id: CallId,
        kind: OutboundMessageKind,
        text: MessageText,
    ) -> bool:
        """True when the message is in the outbox (now or before)."""

        now: Microseconds = self.wall_clock.now_unix()
        for identity in list_reachable_identities(
            self.channel_repo, business.id, contact
        ):
            channel: ChannelDocument | None = find_business_channel(
                self.channel_repo, business.id, identity.channel
            )
            if channel is None or not self._can_carry(business, contact, identity, now):
                continue

            idempotency_key = call_message_idempotency_key(call_id, kind)
            queue_outbound_message(
                self.outbound_message_repo,
                self.job_queue,
                OutboundMessageDocument(
                    id=derive_outbound_message_id(business.id, idempotency_key),
                    business_id=business.id,
                    kind=kind,
                    idempotency_key=idempotency_key,
                    recipient_key=customer_recipient_key(
                        channel.id, identity.channel_user_id
                    ),
                    customer=CustomerRecipient(
                        channel_id=channel.id,
                        channel=identity.channel,
                        channel_user_id=identity.channel_user_id,
                    ),
                    text=text,
                    call_id=call_id,
                    created_at=now,
                    updated_at=now,
                ),
                self.unit_of_work,
            )
            return True

        return False

    def _can_carry(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        identity: ChannelIdentity,
        now: Microseconds,
    ) -> bool:
        return identity.channel not in WINDOWED_CHANNELS or is_messaging_window_open(
            self.conversation_repo,
            self.message_repo,
            business,
            contact,
            identity.channel,
            now,
        )
