"""Google Calendar routes: the cabinet's connection routes and the public
OAuth callback, which only forwards Google's values to the cabinet
(CABINET_BASE_URL); the cabinet finishes connecting for the signed-in owner
through the authenticated completion route."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.operations.business_access import (
    BUSINESS_PREFIX,
    BusinessAuthorizer,
)
from app.gateways.http.operations.query_values import OptionalQuery
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.calendar import (
    CalendarConnectionOutcome,
    CalendarConnectionStatusQuery,
    CalendarConnectionStatusView,
    CompleteCalendarConnectionRequest,
)
from app.schemas.dto.operations.calendar_connection import (
    CalendarConnectUrlView,
    CalendarDisconnectResult,
    CompleteCalendarConnectionCommand,
    DisconnectCalendarCommand,
    StartCalendarConnectionCommand,
)
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.calendar.calendar_return_urls import build_calendar_completion_url

GOOGLE_CALENDAR_CALLBACK_PATH: str = "/v1/integrations/google-calendar/callback"
GOOGLE_CALENDAR_COMPLETE_PATH: str = "/v1/integrations/google-calendar/complete"

read_calendar_completion_body = build_json_body_dependency(
    CompleteCalendarConnectionRequest
)


def build_google_calendar_routes(
    *,
    current_user: CurrentUserDependency,
    authorize: BusinessAuthorizer,
    start_calendar_connection: OperatorContract[
        StartCalendarConnectionCommand, CalendarConnectUrlView
    ],
    complete_calendar_connection: OperatorContract[
        CompleteCalendarConnectionCommand, CalendarConnectionOutcome
    ],
    disconnect_calendar: OperatorContract[
        DisconnectCalendarCommand, CalendarDisconnectResult
    ],
    get_calendar_connection: OperatorContract[
        CalendarConnectionStatusQuery, CalendarConnectionStatusView
    ],
    cabinet_base_url: CabinetBaseUrl | None,
) -> APIRouter:
    """
    Connecting Google Calendar (Bearer auth; owners connect and disconnect)
    and the public OAuth callback that forwards to the cabinet.
    """

    router = APIRouter()

    @router.get(f"{BUSINESS_PREFIX}/integrations/google-calendar/connect-url")
    def get_google_calendar_connect_url(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> CalendarConnectUrlView:
        business: BusinessDocument = authorize(
            user_id, business_id, BusinessMemberRole.OWNER
        )
        return start_calendar_connection.operate(
            StartCalendarConnectionCommand(business_id=business.id, user_id=user_id)
        )

    @router.get(f"{BUSINESS_PREFIX}/integrations/google-calendar")
    def get_google_calendar(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> CalendarConnectionStatusView:
        business: BusinessDocument = authorize(user_id, business_id)
        return get_calendar_connection.operate(
            CalendarConnectionStatusQuery(business_id=business.id)
        )

    @router.get(
        GOOGLE_CALENDAR_CALLBACK_PATH,
        response_class=RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
        responses={
            status.HTTP_303_SEE_OTHER: {
                "description": (
                    "To the cabinet page that finishes connecting for the "
                    "signed-in owner: CABINET_BASE_URL/integrations/"
                    "google-calendar/callback with Google's code, state and "
                    "error."
                )
            }
        },
    )
    def get_google_calendar_callback(
        code: OptionalQuery = None,
        state: OptionalQuery = None,
        error: OptionalQuery = None,
    ) -> Response:
        # Nothing is exchanged here: this public URL cannot tell who brought
        # the code back. The cabinet completes it behind the owner's session.
        if cabinet_base_url is None:
            return render_cabinet_required_page()

        return RedirectResponse(
            str(
                build_calendar_completion_url(
                    cabinet_base_url, {"code": code, "state": state, "error": error}
                )
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @router.post(
        GOOGLE_CALENDAR_COMPLETE_PATH,
        openapi_extra=describe_json_body(CompleteCalendarConnectionRequest),
    )
    def post_google_calendar_completion(
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            CompleteCalendarConnectionRequest, Depends(read_calendar_completion_body)
        ],
    ) -> CalendarConnectionOutcome:
        """
        Finish connecting with Google's callback values; only the user who
        started connecting can (another user's state is an expired link).
        """

        return complete_calendar_connection.operate(
            CompleteCalendarConnectionCommand(
                user_id=user_id,
                state=body.state,
                code=body.code,
                provider_error=body.error,
            )
        )

    @router.delete(f"{BUSINESS_PREFIX}/integrations/google-calendar")
    def delete_google_calendar(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> CalendarDisconnectResult:
        business: BusinessDocument = authorize(
            user_id, business_id, BusinessMemberRole.OWNER
        )
        return disconnect_calendar.operate(
            DisconnectCalendarCommand(business_id=business.id)
        )

    return router


def render_cabinet_required_page() -> HTMLResponse:
    """
    A plain page for the end of Google's consent when CABINET_BASE_URL is
    not configured: connecting is finished only from the cabinet.
    """

    return HTMLResponse(
        content=(
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>Google Calendar</title></head>"
            "<body><p>Google Calendar was not connected: it is connected from "
            "the cabinet, and CABINET_BASE_URL is not configured.</p></body></html>"
        ),
        status_code=status.HTTP_400_BAD_REQUEST,
        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"},
    )
