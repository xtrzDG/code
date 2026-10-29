"""
The reminder job's outbox in memory: the business's messenger channels
(connected, or not connected on demand), the outbox messages it queued and
their delivery jobs, read back in the shape the tests compare.
"""

from collections.abc import Callable

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.repositories.business_repositories import ChannelRepository
from app.repositories.delivery_repositories import OutboundMessageRepository
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.storage.booleans import IsDocumentInserted
from tests.platform.worker_fakes import build_job_stores

MESSENGERS: tuple[ChannelKind, ...] = (
    ChannelKind.TELEGRAM,
    ChannelKind.WHATSAPP,
    ChannelKind.MESSENGER,
    ChannelKind.INSTAGRAM,
)

type SentText = tuple[BusinessId, ChannelKind, ChannelUserId, MessageText]
type SentTemplate = tuple[BusinessId, ChannelUserId, str, str, list[str]]


class HookedOutboundMessageRepository(OutboundMessageRepository):
    """Runs `on_insert` before a message is stored (a change mid-run)."""

    on_insert: Callable[[], None] | None = None

    def insert_if_new(self, message: OutboundMessageDocument) -> IsDocumentInserted:
        if self.on_insert is not None:
            self.on_insert()

        return super().insert_if_new(message)


class ReminderOutbox:
    def __init__(self, wall_clock: WallClock[Microseconds]) -> None:
        self.channel_repo = ChannelRepository(
            InMemoryDocumentCollectionAdapter(ChannelDocument)
        )
        self.outbound_messages = InMemoryDocumentCollectionAdapter(
            OutboundMessageDocument
        )
        self.outbound_message_repo = HookedOutboundMessageRepository(
            self.outbound_messages
        )
        self.jobs = build_job_stores()
        self.job_queue = JobQueueFacilitator(
            self.jobs.job_repo, wall_clock, self.jobs.job_wakeup
        )

    def connect(
        self,
        business_id: BusinessId,
        not_connected: frozenset[ChannelKind] = frozenset(),
    ) -> None:
        """Every messenger of the business; those listed are switched off."""

        for kind in MESSENGERS:
            self.channel_repo.save(
                ChannelDocument(
                    business_id=business_id,
                    kind=kind,
                    external_id=ChannelExternalId(f"{kind.value}-account"),
                    status=(
                        ChannelStatus.DISABLED
                        if kind in not_connected
                        else ChannelStatus.CONNECTED
                    ),
                )
            )

    def reconnect(self, business_id: BusinessId, kind: ChannelKind) -> None:
        for channel in self.channel_repo.list_by_business(business_id):
            if channel.kind is kind:
                channel.status = ChannelStatus.CONNECTED
                self.channel_repo.save(channel)

    def queued(self) -> list[OutboundMessageDocument]:
        """The reminders queued, oldest first."""

        return sorted(
            self.outbound_messages.list_all(),
            key=lambda message: int(message.created_at),
        )

    @property
    def sent(self) -> list[SentText]:
        """Free-text reminders: business, channel, recipient, text."""

        return [
            (
                message.business_id,
                message.customer.channel,
                message.customer.channel_user_id,
                message.text,
            )
            for message in self.queued()
            if message.customer is not None and message.template is None
        ]

    @property
    def templates(self) -> list[SentTemplate]:
        """WhatsApp templates: business, recipient, name, language, values."""

        return [
            (
                message.business_id,
                message.customer.channel_user_id,
                str(message.template.name),
                str(message.template.language_code),
                [str(value) for value in message.template.body_parameters],
            )
            for message in self.queued()
            if message.customer is not None and message.template is not None
        ]

    @property
    def channels(self) -> list[ChannelKind]:
        return [
            message.customer.channel
            for message in self.queued()
            if message.customer is not None
        ]
