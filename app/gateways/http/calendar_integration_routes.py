"""
Settings → Integrations, the Google calendars a resource can be linked to,
and the public iCal export feed of a resource.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.operations.business_access import BusinessAuthorizer
from app.gateways.http.strict_request_parsing import read_client_ip_address
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.dto.calendar_sync.busy_reads import GoogleCalendarList
from app.schemas.dto.calendar_sync.calendar_commands import BusinessCalendarsQuery
from app.schemas.dto.calendar_sync.ical_export import IcalExportFile, IcalExportRequest
from app.schemas.dto.calendar_sync.integrations import IntegrationList
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.calendar_sync.strings import IcalExportToken
from app.schemas.typings.users.prefixed_id import UserId

PUBLIC_ICAL_PATH: str = "/v1/public/ical/{token}.ics"
CALENDAR_MEDIA_TYPE: str = "text/calendar; charset=utf-8"
MAX_TOKEN_LENGTH: int = 128
# The feed is a secret address: never cached on the way, never indexed.
FEED_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "Content-Disposition": 'inline; filename="calendar.ics"',
}
FEED_OPENAPI_RESPONSES: dict[int | str, dict[str, object]] = {
    200: {
        "description": "The resource's busy times as an iCalendar feed.",
        "content": {"text/calendar": {"schema": {"type": "string"}}},
    },
}


def build_calendar_integration_router(
    *,
    current_user: CurrentUserDependency,
    authorize: BusinessAuthorizer,
    list_integrations: OperatorContract[BusinessCalendarsQuery, IntegrationList],
    list_google_calendars: OperatorContract[BusinessCalendarsQuery, GoogleCalendarList],
    export_feed: OperatorContract[IcalExportRequest, IcalExportFile],
) -> APIRouter:
    """
    Routes:
        GET /v1/businesses/{business_id}/integrations
            Settings → Integrations (owners);
        GET /v1/businesses/{business_id}/integrations/google-calendar/calendars
            the connected account's calendars to link a resource to (owners);
        GET /v1/public/ical/{token}.ics
            a resource's busy times for Airbnb, Booking.com or any calendar
            (public: the token is the key; limited per network, 429).
    """

    router = APIRouter(tags=["integrations"], responses=standard_error_responses())

    @router.get("/v1/businesses/{business_id}/integrations")
    def get_business_integrations(
        business_id: str, user_id: Annotated[UserId, Depends(current_user)]
    ) -> IntegrationList:
        business = authorize(user_id, business_id, BusinessMemberRole.OWNER)
        return list_integrations.operate(
            BusinessCalendarsQuery(business_id=business.id)
        )

    @router.get("/v1/businesses/{business_id}/integrations/google-calendar/calendars")
    def get_google_calendars(
        business_id: str, user_id: Annotated[UserId, Depends(current_user)]
    ) -> GoogleCalendarList:
        business = authorize(user_id, business_id, BusinessMemberRole.OWNER)
        return list_google_calendars.operate(
            BusinessCalendarsQuery(business_id=business.id)
        )

    @router.get(
        PUBLIC_ICAL_PATH,
        response_class=Response,
        responses=FEED_OPENAPI_RESPONSES,
        tags=["calendar feeds"],
    )
    def get_public_ical_feed(token: str, request: Request) -> Response:
        feed: IcalExportFile = export_feed.operate(
            IcalExportRequest(
                token=feed_token(token),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(
            content=str(feed.content),
            media_type=CALENDAR_MEDIA_TYPE,
            headers=FEED_HEADERS,
        )

    return router


def feed_token(raw_token: str) -> IcalExportToken:
    """The address's token; a malformed one is simply not found."""

    token: str = raw_token.strip()
    if not token or len(token) > MAX_TOKEN_LENGTH or not token.isascii():
        raise NotFoundError("This calendar address is not valid (any more).")

    return IcalExportToken(token)
