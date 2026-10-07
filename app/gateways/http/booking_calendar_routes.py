"""
The bookings calendar of the cabinet (Bookings → Day, Week, Nights): the
places, their hours and load, and the bookings of a window of local days
in one call. Bookings move with POST …/bookings/{id}/reschedule.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.operations.business_access import (
    BUSINESS_PREFIX,
    build_business_authorizer,
)
from app.gateways.http.operations.query_values import (
    OptionalQuery,
    parse_flag,
    parse_optional_flag,
    parse_optional_integer,
    parse_text,
)
from app.gateways.http.strict_request_parsing import read_client_ip_address
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.booking_grid import BookingGrid, BookingGridQuery
from app.schemas.typings.bookings.constrained_integers import BookingGridDayCount
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.users.prefixed_id import UserId

DEFAULT_GRID_DAYS = BookingGridDayCount(1)


def build_booking_calendar_router(
    *,
    current_user: CurrentUserDependency,
    authorize_business_access: OperatorContract[
        BusinessAccessRequest, BusinessDocument
    ],
    booking_grid: OperatorContract[BookingGridQuery, BookingGrid],
) -> APIRouter:
    """GET /v1/businesses/{business_id}/bookings/grid (owners and staff)."""

    authorize = build_business_authorizer(authorize_business_access)
    router = APIRouter(tags=["operations"], responses=standard_error_responses())

    @router.get(f"{BUSINESS_PREFIX}/bookings/grid")
    def get_booking_grid(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        date: Annotated[str, Query()],
        days: OptionalQuery = None,
        include_sandbox: OptionalQuery = None,
        include_bookings: OptionalQuery = None,
    ) -> BookingGrid:
        """
        The calendar from the local `date` for `days` days (1 to 31, one by
        default) in the business time zone: every place with its opening
        ranges and load per day (unit-minutes for time slots, rooms for
        nights) and the bookings that overlap the window, cancelled ones
        left out. `include_bookings=false` returns the load alone (the
        week's heatmap, not audited); with the bookings the call is
        audited as a view of customers' data.
        """

        business: BusinessDocument = authorize(user_id, business_id)
        return booking_grid.operate(
            BookingGridQuery(
                business_id=business.id,
                actor_id=user_id,
                client_ip_address=read_client_ip_address(request),
                date_from=parse_text(date, LocalDate, "date"),
                days=parse_optional_integer(days, BookingGridDayCount, "days")
                or DEFAULT_GRID_DAYS,
                include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
                include_bookings=parse_optional_flag(
                    include_bookings, "include_bookings"
                )
                is not False,
            )
        )

    return router
