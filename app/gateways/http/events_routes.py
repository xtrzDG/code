"""
The live cabinet: the stream of what changes in a business (Server-Sent
Events) and the counts of what waits for a person, which the cabinet's
navigation badges show and the stream keeps fresh.
"""

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from app.contracts.live_events import (
    LiveEventStreamFacilitatorContract,
    OpenLiveStreamContract,
)
from app.contracts.operator_contract import OperatorContract
from app.gateways.http.live_events.event_stream_chunks import live_event_chunks
from app.gateways.http.live_events.event_stream_format import EVENT_STREAM_MEDIA_TYPE
from app.gateways.http.live_events.event_stream_response import EventStreamResponse
from app.gateways.http.live_events.event_stream_subscriber import (
    EventStreamSubscriber,
)
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.operations.business_access import (
    BUSINESS_PREFIX,
    build_business_authorizer,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.live_events import LiveEventReplay, LiveStreamLimits
from app.schemas.dto.operations.attention_counts import (
    AttentionCounts,
    AttentionCountsQuery,
)
from app.schemas.typings.live_events.constrained_strings import LiveEventId
from app.schemas.typings.users.prefixed_id import UserId

EVENT_STREAM_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {
        "description": (
            "Server-Sent Events: `stream.ready`, then each change of the "
            "business (`id`, `event`, `data` with the kind, the ids and the "
            "time; never customer text), `stream.resync` when the cabinet "
            "should reload what it shows, and a heartbeat comment every "
            "20 s. The stream ends after 15 minutes; reconnect with the "
            "last `id` as Last-Event-ID to get what was missed."
        ),
        "content": {EVENT_STREAM_MEDIA_TYPE: {"schema": {"type": "string"}}},
    },
}


def build_events_router(
    *,
    current_user: CurrentUserDependency,
    authorize_business_access: OperatorContract[
        BusinessAccessRequest, BusinessDocument
    ],
    get_attention_counts: OperatorContract[AttentionCountsQuery, AttentionCounts],
    stream_facilitator: LiveEventStreamFacilitatorContract,
    limits: LiveStreamLimits,
) -> APIRouter:
    """
    Cabinet routes (Bearer auth; owners and staff):
        GET /v1/businesses/{business_id}/events            live stream (SSE)
        GET /v1/businesses/{business_id}/attention-counts  waiting items

    The stream handler is async and holds no request thread while it is
    open: only the access check runs on one, briefly. At most
    `limits.streams_per_user` streams of one person per API process (429).
    """

    authorize = build_business_authorizer(authorize_business_access)
    router = APIRouter(tags=["live"], responses=standard_error_responses())

    @router.get(
        f"{BUSINESS_PREFIX}/events",
        status_code=200,
        response_class=EventStreamResponse,
        responses=EVENT_STREAM_RESPONSES,
    )
    async def stream_live_events(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    ) -> Response:
        """
        What changes in the business, as it happens (see the 200 answer).
        Events name what changed by id; the cabinet reloads it through the
        normal routes, which check access and audit views.
        """

        business: BusinessDocument = await run_in_threadpool(
            authorize, user_id, business_id
        )
        known_event_id, is_unknown = parse_last_event_id(last_event_id)
        subscriber = EventStreamSubscriber(asyncio.get_running_loop())
        stream: OpenLiveStreamContract = stream_facilitator.open(
            user_id, business.id, known_event_id, subscriber
        )
        replay: LiveEventReplay = (
            LiveEventReplay(is_resync_required=True) if is_unknown else stream.replay
        )
        return EventStreamResponse(
            live_event_chunks(replay, subscriber, limits), on_close=stream.close
        )

    @router.get(f"{BUSINESS_PREFIX}/attention-counts")
    def get_attention_counts_route(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AttentionCounts:
        """
        What waits for a person (sandbox excluded): open handoffs, new
        requests, upcoming bookings to confirm and channels in error; the
        badges of the cabinet's navigation. Indexed counts only, no personal
        data, so it records no view.
        """

        business: BusinessDocument = authorize(user_id, business_id)
        return get_attention_counts.operate(
            AttentionCountsQuery(business_id=business.id)
        )

    return router


def parse_last_event_id(raw_value: str | None) -> tuple[LiveEventId | None, bool]:
    """
    The cabinet's Last-Event-ID, and whether it sent one this API cannot
    read (then the stream starts with a resync instead of a replay).
    """

    if raw_value is None or raw_value.strip() == "":
        return None, False

    try:
        return LiveEventId(raw_value.strip()), False
    except ValueError:
        return None, True
