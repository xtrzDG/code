"""
The live routes (event stream and attention counts) on a small FastAPI app
with token login, over the in-memory operations world and bus.
"""

import json
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from app.adapters.events.in_memory_live_event_bus_adapter import (
    InMemoryLiveEventBusAdapter,
)
from app.contracts.live_events import LiveEventBusAdapterContract
from app.facilitators.events.live_event_stream_facilitator import (
    LiveEventStreamFacilitator,
)
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.events_routes import build_events_router
from app.gateways.http.user_authentication import build_current_user_dependency
from app.schemas.dto.live_events import LiveEvent, LiveStreamLimits
from app.schemas.typings.live_events.constrained_floats import (
    LiveStreamHeartbeatSeconds,
    LiveStreamLifetimeSeconds,
)
from app.schemas.typings.live_events.constrained_integers import LiveStreamsPerUser
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.foundation.access_support import ACCESS_SETTINGS
from tests.operations.operations_api import TokenAuthenticator, operator
from tests.operations.operations_world import OperationsWorld

OWNER_TOKEN: str = "owner-token"
STAFF_TOKEN: str = "staff-token"
OTHER_OWNER_TOKEN: str = "other-owner-token"
# Short streams: a test client reads a response to its end.
TEST_LIMITS: LiveStreamLimits = LiveStreamLimits(
    heartbeat_seconds=LiveStreamHeartbeatSeconds(0.1),
    lifetime_seconds=LiveStreamLifetimeSeconds(0.35),
    streams_per_user=LiveStreamsPerUser(2),
)
# Events published this long after a stream was asked for reach it live.
PUBLISH_DELAY_SECONDS: float = 0.12


@dataclass(frozen=True)
class StreamMessage:
    """One SSE message: its name, id (or None) and JSON data."""

    event: str
    id: str | None
    data: dict[str, object]


def parse_stream(text: str) -> list[StreamMessage]:
    messages: list[StreamMessage] = []
    for block in text.split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.split("\n"):
            name, separator, value = line.partition(": ")
            if separator and name in {"id", "event", "data"}:
                fields[name] = value
        if "event" in fields:
            messages.append(
                StreamMessage(
                    event=fields["event"],
                    id=fields.get("id"),
                    data=json.loads(fields.get("data", "{}")),
                )
            )
    return messages


class LiveApi:
    """Business A (owner and staff) and business B with its own owner."""

    def __init__(
        self,
        limits: LiveStreamLimits = TEST_LIMITS,
        bus: LiveEventBusAdapterContract | None = None,
    ) -> None:
        self.world = OperationsWorld()
        self.owner_id, self.staff_id, self.other_owner_id = UserId(), UserId(), UserId()
        self.business = self.world.add_business(
            owner_id=self.owner_id, staff_ids=(self.staff_id,)
        )
        self.other_business = self.world.add_business(
            name="Other", owner_id=self.other_owner_id
        )
        self.bus: LiveEventBusAdapterContract = bus or InMemoryLiveEventBusAdapter()
        self.streams = LiveEventStreamFacilitator(self.bus, limits)
        world = self.world
        application = FastAPI()
        install_error_handlers(application)
        application.include_router(
            build_events_router(
                current_user=build_current_user_dependency(
                    TokenAuthenticator(
                        {
                            OWNER_TOKEN: self.owner_id,
                            STAFF_TOKEN: self.staff_id,
                            OTHER_OWNER_TOKEN: self.other_owner_id,
                        }
                    ),
                    SessionAssuranceContext(),
                ),
                authorize_business_access=operator(
                    AuthorizeBusinessAccessUseCase(
                        business_repo=world.business_repo,
                        user_repo=world.user_repo,
                        audit_log_repo=world.audit_repo,
                        wall_clock=world.clock.wall_clock,
                        session_assurance=SessionAssuranceContext(),
                        app_settings=ACCESS_SETTINGS,
                    )
                ),
                count_inbox_attention=operator(world.count_attention()),
                stream_facilitator=self.streams,
                limits=limits,
            )
        )
        self.client = TestClient(application)

    def url(self, path: str) -> str:
        return f"/v1/businesses/{self.business.id}{path}"

    def stream(
        self,
        token: str = STAFF_TOKEN,
        last_event_id: str | None = None,
        publish: Sequence[LiveEvent] = (),
        meanwhile: Callable[[], object] | None = None,
    ) -> Response:
        """
        Open the stream; `publish` goes on the bus, and `meanwhile` runs,
        while it is open.
        """

        headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
        if last_event_id is not None:
            headers["Last-Event-ID"] = last_event_id

        def while_open() -> None:
            for event in publish:
                self.bus.publish(event)
            if meanwhile is not None:
                meanwhile()

        timer = threading.Timer(PUBLISH_DELAY_SECONDS, while_open)
        timer.start()
        try:
            return self.client.get(self.url("/events"), headers=headers)
        finally:
            timer.join()

    def get(self, path: str, token: str = STAFF_TOKEN) -> Response:
        return self.client.get(
            self.url(path), headers={"Authorization": f"Bearer {token}"}
        )
