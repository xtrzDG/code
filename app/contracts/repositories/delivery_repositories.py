"""
Persistence contracts of the inbox (webhook messages waiting to be
processed) and the outbox (replies and staff notifications waiting to be
sent).

Both insert in one atomic step that refuses a taken id, so a redelivered
webhook or a step that runs again never makes a second copy, not even in
another process. Changes go through `update`: read, change and write the
stored document in one step (a row lock on Postgres).
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.constrained_strings import OutboundRecipientKey
from app.schemas.typings.deliveries.prefixed_id import InboundEventId, OutboundMessageId
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import DocumentCount

type InboundEventChange = Callable[[InboundEventDocument], InboundEventDocument | None]
type OutboundMessageChange = Callable[
    [OutboundMessageDocument], OutboundMessageDocument | None
]


class InboundEventRepoContract(RepoContract, Protocol):
    def insert_if_new(self, event: InboundEventDocument) -> IsDocumentInserted:
        """False, and nothing written, when the event is already stored."""
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId | None,
        event_id: InboundEventId,
    ) -> InboundEventDocument | None:
        """The event of this business (None: a platform event), else None."""
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId | None,
        event_id: InboundEventId,
        change: InboundEventChange,
    ) -> InboundEventDocument | None:
        """
        Store what `change` makes of the event as stored now; None, and
        nothing written, when the event is missing, belongs to another
        business, or `change` returns None.
        """
        raise NotImplementedError

    def delete_created_before(self, created_before: Microseconds) -> DocumentCount:
        raise NotImplementedError


class OutboundMessageRepoContract(RepoContract, Protocol):
    def insert_if_new(self, message: OutboundMessageDocument) -> IsDocumentInserted:
        """False, and nothing written, when the message is already queued."""
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        message_id: OutboundMessageId,
    ) -> OutboundMessageDocument | None:
        raise NotImplementedError

    def get_many(
        self,
        business_id: BusinessId,
        message_ids: Sequence[OutboundMessageId],
    ) -> list[OutboundMessageDocument]:
        """The business's messages of these ids (missing ones skipped), one read."""
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        message_id: OutboundMessageId,
        change: OutboundMessageChange,
    ) -> OutboundMessageDocument | None:
        """As `InboundEventRepoContract.update`."""
        raise NotImplementedError

    def list_pending_for_recipient(
        self,
        business_id: BusinessId,
        recipient_key: OutboundRecipientKey,
    ) -> list[OutboundMessageDocument]:
        """The recipient's messages still waiting, oldest first."""
        raise NotImplementedError

    def delete_created_before(self, created_before: Microseconds) -> DocumentCount:
        raise NotImplementedError
