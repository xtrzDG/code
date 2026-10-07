"""Cabinet routes of bookings: availability, the list, manual bookings,
cancelling, rescheduling, edits and undoing a status change."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.idempotency.idempotency_dependency import (
    NO_IDEMPOTENCY,
    IdempotencyDependency,
)
from app.gateways.http.operations.business_access import (
    BUSINESS_PREFIX,
    BusinessAuthorizer,
)
from app.gateways.http.operations.query_values import (
    OptionalQuery,
    parse_flag,
    parse_optional_integer,
    parse_optional_text,
    parse_path_id,
    parse_text,
)
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.bookings import BookingOrder, BookingStatus, ResourceKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    BookingResult,
    BookingView,
    CancelBookingCommand,
    RescheduleBookingCommand,
)
from app.schemas.dto.operations.bookings import (
    BookingPage,
    ListBookingsQuery,
    ManualBookingCommand,
    ManualBookingRequest,
    RescheduleBookingRequest,
    RevertBookingStatusCommand,
    RevertBookingStatusRequest,
    UpdateBookingCommand,
    UpdateBookingRequest,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    NightCount,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId

read_manual_booking_body = build_json_body_dependency(ManualBookingRequest)
read_reschedule_body = build_json_body_dependency(RescheduleBookingRequest)
read_booking_update_body = build_json_body_dependency(UpdateBookingRequest)
read_revert_status_body = build_json_body_dependency(RevertBookingStatusRequest)


def build_booking_routes(
    *,
    current_user: CurrentUserDependency,
    authorize: BusinessAuthorizer,
    check_availability: OperatorContract[AvailabilityQuery, AvailabilityResult],
    list_bookings: OperatorContract[ListBookingsQuery, BookingPage],
    create_manual_booking: OperatorContract[ManualBookingCommand, BookingResult],
    cancel_booking: OperatorContract[CancelBookingCommand, BookingResult],
    reschedule_booking: OperatorContract[RescheduleBookingCommand, BookingResult],
    update_booking: OperatorContract[UpdateBookingCommand, BookingView],
    revert_booking_status: OperatorContract[RevertBookingStatusCommand, BookingView],
    idempotent: IdempotencyDependency = NO_IDEMPOTENCY,
) -> APIRouter:
    """
    Availability and bookings under /v1/businesses/{business_id} (Bearer
    auth; owners and staff).
    """

    router = APIRouter()

    @router.get(f"{BUSINESS_PREFIX}/availability")
    def get_availability(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        date: Annotated[str, Query()],
        time: OptionalQuery = None,
        party_size: OptionalQuery = None,
        resource_id: OptionalQuery = None,
        resource_kind: OptionalQuery = None,
        service_item_id: OptionalQuery = None,
        duration_minutes: OptionalQuery = None,
        nights: OptionalQuery = None,
        full_day: OptionalQuery = None,
    ) -> AvailabilityResult:
        business: BusinessDocument = authorize(user_id, business_id)
        return check_availability.operate(
            AvailabilityQuery(
                business_id=business.id,
                date=parse_text(date, LocalDate, "date"),
                time=parse_optional_text(time, LocalTimeOfDay, "time"),
                party_size=parse_optional_integer(party_size, PartySize, "party_size"),
                resource_id=parse_optional_text(resource_id, ResourceId, "resource_id"),
                resource_kind=parse_optional_text(
                    resource_kind, ResourceKind, "resource_kind"
                ),
                service_item_id=parse_optional_text(
                    service_item_id, KnowledgeItemId, "service_item_id"
                ),
                duration_minutes=parse_optional_integer(
                    duration_minutes, BookingDurationMinutes, "duration_minutes"
                ),
                nights=parse_optional_integer(nights, NightCount, "nights"),
                full_day=parse_flag(full_day, "full_day"),
            )
        )

    @router.get(f"{BUSINESS_PREFIX}/bookings")
    def get_bookings(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        date_from: Annotated[str | None, Query(alias="from")] = None,
        date_to: Annotated[str | None, Query(alias="to")] = None,
        status: OptionalQuery = None,
        resource_id: OptionalQuery = None,
        include_sandbox: OptionalQuery = None,
        order: OptionalQuery = None,
        limit: OptionalQuery = None,
        cursor: OptionalQuery = None,
    ) -> BookingPage:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_bookings.operate(
            ListBookingsQuery(
                business_id=business.id,
                actor_id=user_id,
                client_ip_address=read_client_ip_address(request),
                date_from=parse_optional_text(date_from, LocalDate, "from"),
                date_to=parse_optional_text(date_to, LocalDate, "to"),
                status=parse_optional_text(status, BookingStatus, "status"),
                resource_id=parse_optional_text(resource_id, ResourceId, "resource_id"),
                include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
                order=parse_optional_text(order, BookingOrder, "order")
                or BookingOrder.EARLIEST_FIRST,
                page=parse_page_request(limit, cursor),
            )
        )

    @router.post(
        f"{BUSINESS_PREFIX}/bookings",
        status_code=201,
        openapi_extra=describe_json_body(ManualBookingRequest),
        dependencies=[Depends(idempotent)],
    )
    def post_booking(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ManualBookingRequest, Depends(read_manual_booking_body)],
    ) -> BookingResult:
        business: BusinessDocument = authorize(user_id, business_id)
        return create_manual_booking.operate(
            ManualBookingCommand(
                business_id=business.id,
                actor_id=user_id,
                contact_name=body.contact_name,
                contact_phone_number=body.contact_phone_number,
                resource_kind=body.resource_kind,
                resource_id=body.resource_id,
                service_item_id=body.service_item_id,
                date=body.date,
                time=body.time,
                duration_minutes=body.duration_minutes,
                nights=body.nights,
                party_size=body.party_size,
                notes=body.notes,
                source_channel=body.source_channel,
                language=body.language,
                country_hint=body.country_hint,
                conversation_id=body.conversation_id,
            )
        )

    @router.post(f"{BUSINESS_PREFIX}/bookings/{{booking_id}}/cancel")
    def post_booking_cancel(
        business_id: str,
        booking_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: OptionalQuery = None,
    ) -> BookingResult:
        business: BusinessDocument = authorize(user_id, business_id)
        return cancel_booking.operate(
            CancelBookingCommand(
                business_id=business.id,
                booking_id=parse_path_id(booking_id, BookingId, "Booking"),
                language=parse_optional_text(language, LanguageTag, "language")
                or business.default_language,
                actor_id=user_id,
            )
        )

    @router.post(
        f"{BUSINESS_PREFIX}/bookings/{{booking_id}}/reschedule",
        openapi_extra=describe_json_body(RescheduleBookingRequest),
    )
    def post_booking_reschedule(
        business_id: str,
        booking_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[RescheduleBookingRequest, Depends(read_reschedule_body)],
        language: OptionalQuery = None,
    ) -> BookingResult:
        business: BusinessDocument = authorize(user_id, business_id)
        return reschedule_booking.operate(
            RescheduleBookingCommand(
                business_id=business.id,
                booking_id=parse_path_id(booking_id, BookingId, "Booking"),
                new_date=body.new_date,
                new_time=body.new_time,
                language=parse_optional_text(language, LanguageTag, "language")
                or business.default_language,
                resource_id=body.new_resource_id,
                expected_date=body.expected_date,
                expected_time=body.expected_time,
            )
        )

    @router.patch(
        f"{BUSINESS_PREFIX}/bookings/{{booking_id}}",
        openapi_extra=describe_json_body(UpdateBookingRequest),
    )
    def patch_booking(
        business_id: str,
        booking_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[UpdateBookingRequest, Depends(read_booking_update_body)],
    ) -> BookingView:
        business: BusinessDocument = authorize(user_id, business_id)
        return update_booking.operate(
            UpdateBookingCommand(
                business_id=business.id,
                actor_id=user_id,
                booking_id=parse_path_id(booking_id, BookingId, "Booking"),
                status=body.status,
                party_size=body.party_size,
                resource_id=body.resource_id,
                notes=body.notes,
                contact_name=body.contact_name,
            )
        )

    @router.post(
        f"{BUSINESS_PREFIX}/bookings/{{booking_id}}/revert-status",
        openapi_extra=describe_json_body(RevertBookingStatusRequest),
    )
    def post_booking_revert_status(
        business_id: str,
        booking_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[RevertBookingStatusRequest, Depends(read_revert_status_body)],
    ) -> BookingView:
        """
        Undo the last status change staff made to the booking (within 10
        minutes): `status` is the status being undone. 409 with a reason
        (nothing_to_undo, status_changed, undo_expired, slot_taken,
        place_gone) when it cannot be undone.
        """

        business: BusinessDocument = authorize(user_id, business_id)
        return revert_booking_status.operate(
            RevertBookingStatusCommand(
                business_id=business.id,
                actor_id=user_id,
                booking_id=parse_path_id(booking_id, BookingId, "Booking"),
                status=body.status,
            )
        )

    return router
