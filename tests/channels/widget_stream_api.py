"""
The website chat's live stream route over the channels testbed, with a
bus that plays a script to each stream it subscribes: the events the
script names, then the end of the stream (no timers: every event is in
the stream's queue before it starts sending).
"""

from collections.abc import Sequence

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from typed_time_provider import Microseconds

from app.adapters.events.in_memory_live_event_bus_adapter import (
    InMemoryLiveEventBusAdapter,
)
from app.contracts.live_events import (
    LiveEventSubscriberContract,
    LiveEventSubscriptionContract,
)
from app.facilitators.events.widget_event_stream_facilitator import (
    WidgetEventStreamFacilitator,
)
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.widget_event_routes import build_widget_event_router
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.dto.channels.widget_streams import (
    WidgetStreamClaims,
    WidgetStreamLimits,
)
from app.schemas.dto.live_events import LiveEvent
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_integers import (
    WidgetStreamsPerAddress,
    WidgetStreamsPerBusiness,
)
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket
from app.schemas.typings.live_events.constrained_strings import LiveEventSubjectId
from app.use_cases.channels.widget_stream.open_widget_stream_use_case import (
    OpenWidgetStreamUseCase,
)
from app.use_cases.channels.widget_stream.read_widget_stream_message_use_case import (
    ReadWidgetStreamMessageUseCase,
)
from app.utilities.channels.widget_stream_tickets import issue_stream_ticket
from app.utilities.channels.widget_visitors import widget_visitor_id
from app.utilities.security.widget_stream_ticket_signer import (
    WidgetStreamTicketSigner,
)
from tests.channels.channels_http import STREAM_TICKET_KEY, wrap_use_case
from tests.channels.testbed import ChannelsTestbed
from tests.live_events.live_event_builders import make_event

TEST_LIMITS: WidgetStreamLimits = WidgetStreamLimits(
    streams_per_business=WidgetStreamsPerBusiness(3),
    streams_per_address=WidgetStreamsPerAddress(2),
)


class ScriptedBus(InMemoryLiveEventBusAdapter):
    """Each new subscriber hears `script`, then the end of its stream."""

    def __init__(self) -> None:
        super().__init__()
        self.script: list[LiveEvent] = []

    def subscribe(
        self,
        business_id: BusinessId,
        subscriber: LiveEventSubscriberContract,
    ) -> LiveEventSubscriptionContract:
        subscription = super().subscribe(business_id, subscriber)
        for event in self.script:
            self.publish(event)
        subscriber.end()
        return subscription


class WidgetStreamApi:
    """The stream route of the testbed's businesses, with real tickets."""

    def __init__(self, testbed: ChannelsTestbed) -> None:
        self.testbed = testbed
        self.signer = WidgetStreamTicketSigner(STREAM_TICKET_KEY)
        self.bus = ScriptedBus()
        self.streams = WidgetEventStreamFacilitator(self.bus, TEST_LIMITS)
        application = FastAPI()
        install_error_handlers(application)
        application.include_router(
            build_widget_event_router(
                open_widget_stream_operator=wrap_use_case(
                    OpenWidgetStreamUseCase(
                        self.signer, testbed.channel_repo, testbed.wall_clock
                    )
                ),
                read_widget_stream_message_operator=wrap_use_case(
                    ReadWidgetStreamMessageUseCase(
                        testbed.message_repo,
                        testbed.conversation_repo,
                        testbed.language_registry,
                    )
                ),
                stream_facilitator=self.streams,
                limits=TEST_LIMITS,
            )
        )
        self.client = TestClient(application)

    def ticket(self, business_id: BusinessId, visitor_key: str) -> WidgetStreamTicket:
        return issue_stream_ticket(
            self.signer,
            business_id,
            visitor_key,
            Microseconds(self.testbed.clock.now_microseconds()),
        )

    def expired_ticket(
        self, business_id: BusinessId, visitor_key: str
    ) -> WidgetStreamTicket:
        return self.signer.sign(
            WidgetStreamClaims(
                business_id=business_id,
                visitor_id=widget_visitor_id(visitor_key),
                expires_at=Microseconds(self.testbed.clock.now_microseconds()),
            )
        )

    def stream(
        self,
        business_id: BusinessId,
        ticket: str | None,
        script: Sequence[LiveEvent] = (),
    ) -> Response:
        self.bus.script = list(script)
        params: dict[str, str] = {} if ticket is None else {"ticket": ticket}
        return self.client.get(f"/v1/widget/{business_id}/events", params=params)


def widget_event(
    business_id: BusinessId,
    kind: LiveEventKind,
    visitor_key: str,
    *subjects: str,
) -> LiveEvent:
    """A widget event naming the visitor of `visitor_key`, then `subjects`."""

    event: LiveEvent = make_event(
        business_id, kind, str(widget_visitor_id(visitor_key))
    )
    return event.model_copy(
        update={
            "ids": [*event.ids, *(LiveEventSubjectId(subject) for subject in subjects)]
        }
    )
