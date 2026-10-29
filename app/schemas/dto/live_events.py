"""
Events of the cabinet's live stream: what changed in a business, by id.

They are hints, not data: the cabinet reloads what an event touches through
the normal API (which checks access and writes the audit entries), so an
event never carries customer text, only the kind of change and ids.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.live_events import LiveEventKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.live_events.booleans import IsLiveResyncRequired
from app.schemas.typings.live_events.constrained_floats import (
    LiveStreamHeartbeatSeconds,
    LiveStreamLifetimeSeconds,
)
from app.schemas.typings.live_events.constrained_integers import LiveStreamsPerUser
from app.schemas.typings.live_events.constrained_strings import (
    LiveEventId,
    LiveEventSubjectId,
)

# An event names at most this many changed things (one booking, one
# handoff and its conversation, ...).
MAX_LIVE_EVENT_SUBJECTS: int = 8


class LiveEvent(ImmutableDTO):
    """
    One change in a business: its kind (`event`) and the ids it touched
    (`ids`). `id` orders nothing; the cabinet sends the last one it saw as
    `Last-Event-ID` when it reconnects.
    """

    id: LiveEventId
    business_id: BusinessId
    event: LiveEventKind
    ids: list[LiveEventSubjectId] = Field(
        default_factory=list[LiveEventSubjectId],
        max_length=MAX_LIVE_EVENT_SUBJECTS,
    )
    occurred_at: Microseconds


class LiveEventReplay(ImmutableDTO):
    """
    What a reconnecting stream sends before the live events: the events of
    the business published after the last one the cabinet saw, or, when
    those are no longer known, the request to reload everything.
    """

    events: list[LiveEvent] = Field(default_factory=list[LiveEvent])
    is_resync_required: IsLiveResyncRequired = False


class LiveStreamLimits(ImmutableDTO):
    """
    How the API keeps live streams: a heartbeat comment every
    `heartbeat_seconds` of quiet, each stream ended after
    `lifetime_seconds` (the cabinet reconnects with its Last-Event-ID), and
    at most `streams_per_user` streams of one person on one process.
    """

    heartbeat_seconds: LiveStreamHeartbeatSeconds = LiveStreamHeartbeatSeconds(20.0)
    lifetime_seconds: LiveStreamLifetimeSeconds = LiveStreamLifetimeSeconds(900.0)
    streams_per_user: LiveStreamsPerUser = LiveStreamsPerUser(5)
