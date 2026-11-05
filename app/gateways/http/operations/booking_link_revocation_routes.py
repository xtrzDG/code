"""Cabinet route that ends the manage links of a booking sent so far."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.operations.business_access import (
    BUSINESS_PREFIX,
    build_business_authorizer,
)
from app.gateways.http.operations.query_values import parse_path_id
from app.gateways.http.strict_request_parsing import read_client_ip_address
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.booking_manage import RevokeBookingLinksCommand
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.users.prefixed_id import UserId


def build_booking_link_revocation_router(
    *,
    current_user: CurrentUserDependency,
    authorize_business_access: OperatorContract[
        BusinessAccessRequest, BusinessDocument
    ],
    revoke_booking_links: OperatorContract[RevokeBookingLinksCommand, None],
) -> APIRouter:
    """
    Routes:
        POST /v1/businesses/{business_id}/bookings/{booking_id}/manage-links/revoke
            every manage link of the booking sent so far stops opening (a
            new link generation; owners and staff; audited); 204
    """

    authorize = build_business_authorizer(authorize_business_access)
    router = APIRouter(tags=["operations"], responses=standard_error_responses())

    @router.post(
        f"{BUSINESS_PREFIX}/bookings/{{booking_id}}/manage-links/revoke",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def post_booking_links_revoke(
        request: Request,
        business_id: str,
        booking_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        business: BusinessDocument = authorize(user_id, business_id)
        revoke_booking_links.operate(
            RevokeBookingLinksCommand(
                business_id=business.id,
                booking_id=parse_path_id(booking_id, BookingId, "Booking"),
                actor_id=user_id,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
