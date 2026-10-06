"""
The website chat's live stream: a visitor's widget hears when a worker
starts writing its answer and when the answer is ready, instead of
polling for it (Server-Sent Events, public like the other widget routes).
"""

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from app.contracts.live_events import LiveEventSubscriptionContract
from app.contracts.operator_contract import OperatorContract
from app.contracts.widget_streams import WidgetEventStreamFacilitatorContract
from app.gateways.http.live_events.event_stream_format import EVENT_STREAM_MEDIA_TYPE
from app.gateways.http.live_events.event_stream_response import EventStreamResponse
from app.gateways.http.live_events.event_stream_subscriber import (
    EventStreamSubscriber,
)
from app.gateways.http.live_events.widget_event_chunks import widget_event_chunks
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.widget_origin_guard import WidgetOriginGuard
from app.schemas.dto.channels.widget_streams import (
    WidgetStreamGrant,
    WidgetStreamLimits,
    WidgetStreamMessageQuery,
    WidgetStreamMessageView,
    WidgetStreamRequest,
)
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.prefixed_id import MessageId

WIDGET_EVENTS_PATH: str = "/v1/widget/{business_id}/events"
WIDGET_EVENT_STREAM_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {
        "description": (
            "Server-Sent Events of one visitor: `stream.ready`, then "
            "`typing_started` when a worker starts writing the visitor's "
            "answer and `answer_ready` when it (or a staff message) is "
            "stored: `message_id`, `author`, `direction` and, for a model "
            "reply the reply guard passed as CLEAN, its `text` (otherwise "
            "the widget polls GET .../messages, which replaces any draft "
            "with the stored text). `stream.resync` asks for one poll; a "
            "heartbeat comment every 20 s; the stream ends after 15 "
            "minutes and the browser reconnects with the same ticket."
        ),
        "content": {EVENT_STREAM_MEDIA_TYPE: {"schema": {"type": "string"}}},
    },
}


def build_widget_event_router(
    open_widget_stream_operator: OperatorContract[
        WidgetStreamRequest, WidgetStreamGrant
    ],
    read_widget_stream_message_operator: OperatorContract[
        WidgetStreamMessageQuery, WidgetStreamMessageView | None
    ],
    stream_facilitator: WidgetEventStreamFacilitatorContract,
    limits: WidgetStreamLimits,
    widget_origin_guard: WidgetOriginGuard | None = None,
) -> APIRouter:
    """
    Routes (public; the visitor is named by a stream ticket, never by the
    visitor key, which stays out of addresses and logs):
        GET /v1/widget/{business_id}/events?ticket=<stream ticket>
            the visitor's live stream (EventSource). The ticket comes with
            the answers to POST and GET .../messages; an unknown, foreign
            or expired one is refused with 401 (the widget polls and gets
            a fresh one), a chat that is off with 404, a website the
            business does not allow with 403, and too many open streams of
            the business or the network with 429.

    Only the access checks run on a request thread, briefly; the open
    stream holds none.
    """

    router = APIRouter(tags=["channels"], responses=standard_error_responses())

    @router.get(
        WIDGET_EVENTS_PATH,
        status_code=200,
        response_class=EventStreamResponse,
        responses=WIDGET_EVENT_STREAM_RESPONSES,
    )
    async def stream_widget_events(
        request: Request,
        business_id: str,
        ticket: Annotated[str | None, Query()] = None,
    ) -> Response:
        """The visitor's typing and answers, as they happen (see the 200 answer)."""

        if widget_origin_guard is not None:
            await run_in_threadpool(widget_origin_guard, request, business_id)
        client_ip_address: ClientIpAddress | None = read_client_ip_address(request)
        grant: WidgetStreamGrant = await run_in_threadpool(
            open_widget_stream_operator.operate,
            WidgetStreamRequest(
                business_id=parse_path_identifier(business_id, BusinessId, "Chat"),
                ticket=parse_stream_ticket(ticket),
                client_ip_address=client_ip_address,
            ),
        )
        subscriber = EventStreamSubscriber(asyncio.get_running_loop())
        subscription: LiveEventSubscriptionContract = stream_facilitator.open(
            grant.business_id, grant.visitor_id, client_ip_address, subscriber
        )

        async def read_message(message_id: MessageId) -> WidgetStreamMessageView | None:
            return await run_in_threadpool(
                read_widget_stream_message_operator.operate,
                WidgetStreamMessageQuery(
                    business_id=grant.business_id,
                    visitor_id=grant.visitor_id,
                    message_id=message_id,
                ),
            )

        return EventStreamResponse(
            widget_event_chunks(subscriber, limits, read_message),
            on_close=subscription.cancel,
        )

    return router


def parse_stream_ticket(raw_ticket: str | None) -> WidgetStreamTicket:
    """A missing or malformed ticket is refused like a forged one (401)."""

    try:
        return WidgetStreamTicket((raw_ticket or "").strip())
    except ValueError as error:
        raise AuthenticationRequiredError(
            "The live chat stream needs the ticket of a widget answer."
        ) from error
