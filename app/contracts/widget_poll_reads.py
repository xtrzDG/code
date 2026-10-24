"""The website widget's poll read in one statement (Postgres)."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.channels.widget_poll_reads import WidgetPollRead
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit


class WidgetPollReadAdapterContract(AdapterContract, Protocol):
    """
    Every open web chat polls every 4 s, and most polls find nothing new:
    what a poll needs is read in one statement and one round trip (Postgres;
    without a database the poll reads through its repositories instead).
    """

    def read_poll(
        self,
        business_id: BusinessId,
        visitor: ChannelUserId,
        after: MessageId | None,
        window: KeysetReadLimit,
    ) -> WidgetPollRead:
        """
        The business's allowed widget websites, the visitor's web-chat
        conversations (no sandbox ones, the current first), where the
        newest `window` messages of those stand and, when `after` is among
        them, the messages after it in full: one snapshot, so a message
        written meanwhile is either all there or comes with the next poll.

        Reads in the ambient storage scope (row-level security as for the
        repositories) and only the given business's rows. Raises
        UnscopedStorageAccessError outside a scope.
        """
        raise NotImplementedError
