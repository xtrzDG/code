"""
The cabinet's live event stream: use cases publish what changed in a
business; open cabinets of that business hear it within a second.

Publishing goes through `EventPublisherFacilitatorContract` (never raises:
an event is a hint, the data is already stored). The transport is a
`LiveEventBusAdapterContract`: Postgres LISTEN/NOTIFY between processes, or
in memory inside one process (development, tests). The SSE route opens
streams through `LiveEventStreamFacilitatorContract`, which limits the
streams of one person and replays what a reconnecting cabinet missed.
"""

from collections.abc import Sequence
from typing import Protocol

from base_typed_id import BasePrefixedTypedId

from app.contracts.adapter_contract import AdapterContract
from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.dto.live_events import LiveEvent, LiveEventReplay
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.live_events.constrained_strings import LiveEventId
from app.schemas.typings.users.prefixed_id import UserId


class LiveEventSubscriberContract(Protocol):
    """
    One open stream, receiving the events of its business. Called from any
    thread (the listener's, a request's, the worker's): implementations
    hand the event over and return at once, never block.
    """

    def deliver(self, event: LiveEvent) -> None:
        raise NotImplementedError

    def resync(self) -> None:
        """Events may have been lost: the cabinet should reload what it shows."""
        raise NotImplementedError

    def end(self) -> None:
        """The server is shutting down: close the stream (the cabinet reconnects)."""
        raise NotImplementedError


class LiveEventSubscriptionContract(Protocol):
    """A subscriber's place on the bus; `cancel` it when the stream closes."""

    def cancel(self) -> None:
        raise NotImplementedError


class LiveEventBusAdapterContract(AdapterContract, Protocol):
    """Carries live events to the open streams of every API process."""

    def publish(self, event: LiveEvent) -> None:
        """Send the event to every process. Raises ExternalServiceError."""
        raise NotImplementedError

    def subscribe(
        self,
        business_id: BusinessId,
        subscriber: LiveEventSubscriberContract,
    ) -> LiveEventSubscriptionContract:
        """Deliver the business's events to `subscriber` until cancelled."""
        raise NotImplementedError

    def replay_after(
        self,
        business_id: BusinessId,
        event_id: LiveEventId,
    ) -> list[LiveEvent] | None:
        """
        The business's events this process heard after `event_id`, oldest
        first; None when it does not know `event_id` (too old, or heard
        before this process started), so the caller must resync.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Stop listening and end every open stream (shutdown)."""
        raise NotImplementedError


class EventPublisherFacilitatorContract(FacilitatorContract, Protocol):
    def publish(
        self,
        business_id: BusinessId,
        event: LiveEventKind,
        ids: Sequence[BasePrefixedTypedId] = (),
        is_sandbox: IsSandboxConversation = False,
    ) -> None:
        """
        Tell the business's open cabinets what changed (by id, never with
        customer text). Sandbox activity (the owner's test chat, autotests)
        is not announced: the cabinet's lists and badges leave it out. Never
        raises: a lost event only delays the cabinet's update until its
        next reload.
        """
        raise NotImplementedError


class OpenLiveStreamContract(Protocol):
    """A stream the facilitator opened: what to send first, and how to close it."""

    @property
    def replay(self) -> LiveEventReplay:
        raise NotImplementedError

    def close(self) -> None:
        """Unsubscribe and give the person's stream slot back (idempotent)."""
        raise NotImplementedError


class LiveEventStreamFacilitatorContract(FacilitatorContract, Protocol):
    def open(
        self,
        user_id: UserId,
        business_id: BusinessId,
        last_event_id: LiveEventId | None,
        subscriber: LiveEventSubscriberContract,
    ) -> OpenLiveStreamContract:
        """
        Subscribe an authorized person's stream to the business. Raises
        RateLimitedError when the person already has the most streams open
        on this process.
        """
        raise NotImplementedError
