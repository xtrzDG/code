"""Cabinet HTTP API of the operations module: availability, bookings, leads,
handoffs, unanswered questions, dashboard and Google Calendar.

Path and query parameters arrive as raw strings and are converted to typed
primitives here (the transport boundary). JSON bodies are validated in JSON
mode, so enum values and typed strings parse strictly from their wire form,
and are described for OpenAPI so the cabinet's generated client knows them.
Lists are paged with `?limit=N&cursor=…`.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.bookings import (
    BookingOrder,
    BookingStatus,
    LeadStatus,
    ResourceKind,
)
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    BookingResult,
    BookingView,
    CancelBookingCommand,
    LeadView,
    RescheduleBookingCommand,
)
from app.schemas.dto.calendar import (
    CalendarConnectionOutcome,
    CalendarConnectionStatusQuery,
    CalendarConnectionStatusView,
    CompleteCalendarConnectionRequest,
)
from app.schemas.dto.operations.bookings import (
    BookingPage,
    ListBookingsQuery,
    ManualBookingCommand,
    ManualBookingRequest,
    RescheduleBookingRequest,
    UpdateBookingCommand,
    UpdateBookingRequest,
)
from app.schemas.dto.operations.calendar_connection import (
    CalendarConnectUrlView,
    CalendarDisconnectResult,
    CompleteCalendarConnectionCommand,
    DisconnectCalendarCommand,
    StartCalendarConnectionCommand,
)
from app.schemas.dto.operations.dashboard import DashboardStats, DashboardStatsQuery
from app.schemas.dto.operations.handoffs import (
    HandoffListItem,
    HandoffPage,
    ListHandoffsQuery,
    ResolveHandoffCommand,
)
from app.schemas.dto.operations.leads import (
    LeadPage,
    ListLeadsQuery,
    UpdateLeadStatusCommand,
    UpdateLeadStatusRequest,
)
from app.schemas.dto.operations.unanswered_questions import (
    AnsweredQuestionResult,
    AnswerUnansweredQuestionCommand,
    AnswerUnansweredQuestionRequest,
    ListUnansweredQuestionsQuery,
    UnansweredQuestionPage,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    NightCount,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId, ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.calendar.calendar_return_urls import build_calendar_completion_url

BUSINESS_PREFIX: str = "/v1/businesses/{business_id}"
GOOGLE_CALENDAR_CALLBACK_PATH: str = "/v1/integrations/google-calendar/callback"
GOOGLE_CALENDAR_COMPLETE_PATH: str = "/v1/integrations/google-calendar/complete"
TRUE_QUERY_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})
FALSE_QUERY_VALUES: frozenset[str] = frozenset({"0", "false", "no", "off"})

type OptionalQuery = Annotated[str | None, Query()]

read_manual_booking_body = build_json_body_dependency(ManualBookingRequest)
read_reschedule_body = build_json_body_dependency(RescheduleBookingRequest)
read_booking_update_body = build_json_body_dependency(UpdateBookingRequest)
read_lead_status_body = build_json_body_dependency(UpdateLeadStatusRequest)
read_answer_body = build_json_body_dependency(AnswerUnansweredQuestionRequest)
read_calendar_completion_body = build_json_body_dependency(
    CompleteCalendarConnectionRequest
)


def build_operations_router(
    *,
    current_user: CurrentUserDependency,
    authorize_business_access: OperatorContract[
        BusinessAccessRequest, BusinessDocument
    ],
    check_availability: OperatorContract[AvailabilityQuery, AvailabilityResult],
    list_bookings: OperatorContract[ListBookingsQuery, BookingPage],
    create_manual_booking: OperatorContract[ManualBookingCommand, BookingResult],
    cancel_booking: OperatorContract[CancelBookingCommand, BookingResult],
    reschedule_booking: OperatorContract[RescheduleBookingCommand, BookingResult],
    update_booking: OperatorContract[UpdateBookingCommand, BookingView],
    list_leads: OperatorContract[ListLeadsQuery, LeadPage],
    update_lead_status: OperatorContract[UpdateLeadStatusCommand, LeadView],
    list_handoffs: OperatorContract[ListHandoffsQuery, HandoffPage],
    resolve_handoff: OperatorContract[ResolveHandoffCommand, HandoffListItem],
    list_unanswered_questions: OperatorContract[
        ListUnansweredQuestionsQuery, UnansweredQuestionPage
    ],
    answer_unanswered_question: OperatorContract[
        AnswerUnansweredQuestionCommand, AnsweredQuestionResult
    ],
    get_dashboard_stats: OperatorContract[DashboardStatsQuery, DashboardStats],
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
    Cabinet routes under /v1/businesses/{business_id} (Bearer auth; owners
    and staff, owner only where noted) plus the Google OAuth callback: the
    public callback only forwards Google's values to the cabinet
    (CABINET_BASE_URL), which finishes connecting for the signed-in owner
    through the authenticated completion route.
    """

    router = APIRouter(tags=["operations"])

    def authorize(
        user_id: UserId,
        raw_business_id: str,
        required_role: BusinessMemberRole | None = None,
    ) -> BusinessDocument:
        return authorize_business_access.operate(
            BusinessAccessRequest(
                user_id=user_id,
                business_id=parse_path_id(raw_business_id, BusinessId, "Business"),
                required_role=required_role,
            )
        )

    @router.get(f"{BUSINESS_PREFIX}/availability")
    def get_availability(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        date: Annotated[str, Query()],
        time: OptionalQuery = None,
        party_size: OptionalQuery = None,
        resource_id: OptionalQuery = None,
        resource_kind: OptionalQuery = None,
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
                duration_minutes=parse_optional_integer(
                    duration_minutes, BookingDurationMinutes, "duration_minutes"
                ),
                nights=parse_optional_integer(nights, NightCount, "nights"),
                full_day=parse_flag(full_day, "full_day"),
            )
        )

    @router.get(f"{BUSINESS_PREFIX}/bookings")
    def get_bookings(
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

    @router.get(f"{BUSINESS_PREFIX}/leads")
    def get_leads(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        status: OptionalQuery = None,
        include_sandbox: OptionalQuery = None,
        limit: OptionalQuery = None,
        cursor: OptionalQuery = None,
    ) -> LeadPage:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_leads.operate(
            ListLeadsQuery(
                business_id=business.id,
                actor_id=user_id,
                status=parse_optional_text(status, LeadStatus, "status"),
                include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
                page=parse_page_request(limit, cursor),
            )
        )

    @router.patch(
        f"{BUSINESS_PREFIX}/leads/{{lead_id}}",
        openapi_extra=describe_json_body(UpdateLeadStatusRequest),
    )
    def patch_lead(
        business_id: str,
        lead_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[UpdateLeadStatusRequest, Depends(read_lead_status_body)],
    ) -> LeadView:
        business: BusinessDocument = authorize(user_id, business_id)
        return update_lead_status.operate(
            UpdateLeadStatusCommand(
                business_id=business.id,
                lead_id=parse_path_id(lead_id, LeadId, "Lead"),
                status=body.status,
            )
        )

    @router.get(f"{BUSINESS_PREFIX}/handoffs")
    def get_handoffs(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        status: OptionalQuery = None,
        is_open: OptionalQuery = None,
        include_sandbox: OptionalQuery = None,
        limit: OptionalQuery = None,
        cursor: OptionalQuery = None,
    ) -> HandoffPage:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_handoffs.operate(
            ListHandoffsQuery(
                business_id=business.id,
                actor_id=user_id,
                status=parse_optional_text(status, HandoffStatus, "status"),
                is_open=parse_optional_flag(is_open, "is_open"),
                include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
                page=parse_page_request(limit, cursor),
            )
        )

    @router.post(f"{BUSINESS_PREFIX}/handoffs/{{handoff_id}}/resolve")
    def post_handoff_resolve(
        business_id: str,
        handoff_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> HandoffListItem:
        business: BusinessDocument = authorize(user_id, business_id)
        return resolve_handoff.operate(
            ResolveHandoffCommand(
                business_id=business.id,
                handoff_id=parse_path_id(handoff_id, HandoffId, "Handoff"),
            )
        )

    @router.get(f"{BUSINESS_PREFIX}/unanswered-questions")
    def get_unanswered_questions(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        include_resolved: OptionalQuery = None,
        include_sandbox: OptionalQuery = None,
        limit: OptionalQuery = None,
        cursor: OptionalQuery = None,
    ) -> UnansweredQuestionPage:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_unanswered_questions.operate(
            ListUnansweredQuestionsQuery(
                business_id=business.id,
                include_resolved=parse_flag(include_resolved, "include_resolved"),
                include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
                page=parse_page_request(limit, cursor),
            )
        )

    @router.post(
        f"{BUSINESS_PREFIX}/unanswered-questions/{{question_id}}/answer",
        openapi_extra=describe_json_body(AnswerUnansweredQuestionRequest),
    )
    def post_unanswered_question_answer(
        business_id: str,
        question_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AnswerUnansweredQuestionRequest, Depends(read_answer_body)],
    ) -> AnsweredQuestionResult:
        business: BusinessDocument = authorize(
            user_id, business_id, BusinessMemberRole.OWNER
        )
        return answer_unanswered_question.operate(
            AnswerUnansweredQuestionCommand(
                business_id=business.id,
                question_id=parse_path_id(
                    question_id, UnansweredQuestionId, "Question"
                ),
                answer=body.answer,
                title=body.title,
            )
        )

    @router.get(f"{BUSINESS_PREFIX}/dashboard")
    def get_dashboard(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        date_from: Annotated[str | None, Query(alias="from")] = None,
        date_to: Annotated[str | None, Query(alias="to")] = None,
    ) -> DashboardStats:
        business: BusinessDocument = authorize(user_id, business_id)
        return get_dashboard_stats.operate(
            DashboardStatsQuery(
                business_id=business.id,
                date_from=parse_optional_text(date_from, LocalDate, "from"),
                date_to=parse_optional_text(date_to, LocalDate, "to"),
            )
        )

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


def parse_path_id[Value](
    raw_value: str,
    id_type: Callable[[str], Value],
    entity: str,
) -> Value:
    """A malformed id in the path is reported as a missing entity."""

    try:
        return id_type(raw_value)
    except (ValueError, TypeError) as error:
        raise NotFoundError(f"{entity} {raw_value} was not found.") from error


def parse_text[Value](
    raw_value: str,
    value_type: Callable[[str], Value],
    name: str,
) -> Value:
    try:
        return value_type(raw_value)
    except (ValueError, TypeError) as error:
        raise ValidationFailedError(f"Invalid {name}: {raw_value!r}.") from error


def parse_optional_text[Value](
    raw_value: str | None,
    value_type: Callable[[str], Value],
    name: str,
) -> Value | None:
    if raw_value is None or raw_value == "":
        return None

    return parse_text(raw_value, value_type, name)


def parse_optional_integer[Value](
    raw_value: str | None,
    value_type: Callable[[int], Value],
    name: str,
) -> Value | None:
    if raw_value is None or raw_value == "":
        return None

    try:
        return value_type(int(raw_value))
    except (ValueError, TypeError) as error:
        raise ValidationFailedError(f"Invalid {name}: {raw_value!r}.") from error


def parse_flag(raw_value: str | None, name: str) -> bool:
    return parse_optional_flag(raw_value, name) or False


def parse_optional_flag(raw_value: str | None, name: str) -> bool | None:
    """True, False, or None when the parameter is missing or empty."""

    if raw_value is None or raw_value == "":
        return None

    normalized: str = raw_value.strip().lower()
    if normalized in TRUE_QUERY_VALUES:
        return True

    if normalized in FALSE_QUERY_VALUES:
        return False

    raise ValidationFailedError(f"Invalid {name}: {raw_value!r} (use true or false).")
