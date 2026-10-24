"""A guest's booking page behind its manage link (public, no bearer token)."""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    read_client_ip_address,
)
from app.schemas.constants.bookings import ManagedBookingRefusalCode
from app.schemas.dto.booking_manage import (
    BookingCalendarFile,
    ManagedBookingRequest,
    ManagedBookingSlots,
    ManagedBookingView,
    RescheduleManagedBookingBody,
)
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.constrained_strings import (
    BookingManageToken,
    LocalDate,
)
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage

PUBLIC_BOOKING_PATH: str = "/v1/public/bookings/{token}"
CALENDAR_MEDIA_TYPE: str = "text/calendar; charset=utf-8"
INVALID_LINK_MESSAGE: str = "This booking link is not valid. Check the link."
# The page is the guest's own: never cached on the way, never indexed, and
# its address (the token) is not passed on as a referrer.
PRIVATE_PAGE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex",
    "Referrer-Policy": "no-referrer",
}
CALENDAR_OPENAPI_RESPONSES: dict[int | str, dict[str, object]] = {
    200: {
        "description": "The booking as an iCalendar file.",
        "content": {"text/calendar": {"schema": {"type": "string"}}},
    },
}

type ManagedBookingOperator[Output] = OperatorContract[ManagedBookingRequest, Output]

read_reschedule_body = build_json_body_dependency(RescheduleManagedBookingBody)


def build_public_booking_router(
    view_operator: ManagedBookingOperator[ManagedBookingView],
    calendar_operator: ManagedBookingOperator[BookingCalendarFile],
    slots_operator: ManagedBookingOperator[ManagedBookingSlots],
    cancel_operator: ManagedBookingOperator[ManagedBookingView],
    reschedule_operator: ManagedBookingOperator[ManagedBookingView],
) -> APIRouter:
    """
    Routes (public; the signed token of the guest's link is the key):
        GET  /v1/public/bookings/{token}
            the booking as its page shows it (no contact details), with the
            ways to write to the business and what may still change;
        GET  /v1/public/bookings/{token}/calendar.ics
            the booking as an .ics file;
        GET  /v1/public/bookings/{token}/slots?date=YYYY-MM-DD
            free times to move it to on a date;
        POST /v1/public/bookings/{token}/cancel
            cancel it (a customer request: staff are notified);
        POST /v1/public/bookings/{token}/reschedule  {"date", "time"}
            move it; the answer carries the moved booking's new token.
    A forged or expired link and a link of a booking moved since are 404
    (reasons `link_invalid`, `link_expired`, `booking_changed`); a booking
    that cannot change any more is 409 (`not_active`, `already_started`,
    or a booking refusal such as `taken`). Requests are limited per link,
    per network and for the platform (429 with Retry-After).
    """

    router: APIRouter = APIRouter(
        tags=["bookings"], responses=standard_error_responses()
    )

    @router.get(PUBLIC_BOOKING_PATH)
    def get_managed_booking(
        token: str, request: Request, response: Response
    ) -> ManagedBookingView:
        response.headers.update(PRIVATE_PAGE_HEADERS)
        return view_operator.operate(manage_request(token, request))

    @router.get(
        f"{PUBLIC_BOOKING_PATH}/calendar.ics",
        response_class=Response,
        responses=CALENDAR_OPENAPI_RESPONSES,
    )
    def get_managed_booking_calendar(token: str, request: Request) -> Response:
        calendar: BookingCalendarFile = calendar_operator.operate(
            manage_request(token, request)
        )
        file_name: str = str(calendar.file_name)
        return Response(
            content=str(calendar.content),
            media_type=CALENDAR_MEDIA_TYPE,
            headers={
                **PRIVATE_PAGE_HEADERS,
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": (
                    f'attachment; filename="{file_name}"; '
                    f"filename*=UTF-8''{quote(file_name)}"
                ),
            },
        )

    @router.get(f"{PUBLIC_BOOKING_PATH}/slots")
    def get_managed_booking_slots(
        token: str, request: Request, response: Response, date: str | None = None
    ) -> ManagedBookingSlots:
        response.headers.update(PRIVATE_PAGE_HEADERS)
        return slots_operator.operate(
            manage_request(token, request).model_copy(
                update={"date": parse_optional(date, LocalDate, "date")}
            )
        )

    @router.post(f"{PUBLIC_BOOKING_PATH}/cancel")
    def cancel_managed_booking(
        token: str, request: Request, response: Response
    ) -> ManagedBookingView:
        response.headers.update(PRIVATE_PAGE_HEADERS)
        return cancel_operator.operate(manage_request(token, request))

    @router.post(
        f"{PUBLIC_BOOKING_PATH}/reschedule",
        openapi_extra=describe_json_body(RescheduleManagedBookingBody),
    )
    def reschedule_managed_booking(
        token: str,
        request: Request,
        response: Response,
        body: Annotated[RescheduleManagedBookingBody, Depends(read_reschedule_body)],
    ) -> ManagedBookingView:
        response.headers.update(PRIVATE_PAGE_HEADERS)
        return reschedule_operator.operate(
            manage_request(token, request).model_copy(
                update={"date": body.date, "time": body.time}
            )
        )

    return router


def manage_request(raw_token: str, request: Request) -> ManagedBookingRequest:
    """The link's token as a typed value; a malformed one is not found."""

    try:
        token = BookingManageToken(raw_token.strip())
    except ValueError as error:
        raise NotFoundError(
            INVALID_LINK_MESSAGE,
            reasons=[
                ErrorReason(
                    code=ErrorReasonCode(ManagedBookingRefusalCode.LINK_INVALID.value),
                    message=ErrorReasonMessage(INVALID_LINK_MESSAGE),
                )
            ],
        ) from error

    return ManagedBookingRequest(
        token=token, client_ip_address=read_client_ip_address(request)
    )
