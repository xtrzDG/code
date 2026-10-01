"""Cabinet HTTP API of the operations module: availability, bookings, leads,
handoffs, unanswered questions, dashboard and Google Calendar.

Path and query parameters arrive as raw strings and are converted to typed
primitives here (the transport boundary). JSON bodies are validated in JSON
mode, so enum values and typed strings parse strictly from their wire form.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, ValidationError

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.bookings import BookingStatus, LeadStatus, ResourceKind
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
)
from app.schemas.dto.operations import (
    AnsweredQuestionResult,
    AnswerUnansweredQuestionCommand,
    AnswerUnansweredQuestionRequest,
    BookingListView,
    CalendarConnectUrlView,
    CalendarDisconnectResult,
    CompleteCalendarConnectionCommand,
    DashboardStats,
    DashboardStatsQuery,
    DisconnectCalendarCommand,
    HandoffListItem,
    HandoffListView,
    LeadListView,
    ListBookingsQuery,
    ListHandoffsQuery,
    ListLeadsQuery,
    ListUnansweredQuestionsQuery,
    ManualBookingCommand,
    ManualBookingRequest,
    RescheduleBookingRequest,
    ResolveHandoffCommand,
    StartCalendarConnectionCommand,
    UnansweredQuestionListView,
    UpdateBookingStatusCommand,
    UpdateBookingStatusRequest,
    UpdateLeadStatusCommand,
    UpdateLeadStatusRequest,
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
from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationCode,
    CalendarAuthorizationState,
    CalendarProviderErrorCode,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.calendar.calendar_return_urls import build_calendar_return_url

BUSINESS_PREFIX: str = "/v1/businesses/{business_id}"
GOOGLE_CALENDAR_CALLBACK_PATH: str = "/v1/integrations/google-calendar/callback"
# Google's `error` and `state` values are short; longer ones are cut.
MAX_CALLBACK_VALUE_LENGTH: int = 512
TRUE_QUERY_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})
FALSE_QUERY_VALUES: frozenset[str] = frozenset({"0", "false", "no", "off"})

type OptionalQuery = Annotated[str | None, Query()]


def build_operations_router(
    *,
    current_user: CurrentUserDependency,
    authorize_business_access: OperatorContract[
        BusinessAccessRequest, BusinessDocument
    ],
    check_availability: OperatorContract[AvailabilityQuery, AvailabilityResult],
    list_bookings: OperatorContract[ListBookingsQuery, BookingListView],
    create_manual_booking: OperatorContract[ManualBookingCommand, BookingResult],
    cancel_booking: OperatorContract[CancelBookingCommand, BookingResult],
    reschedule_booking: OperatorContract[RescheduleBookingCommand, BookingResult],
    update_booking_status: OperatorContract[UpdateBookingStatusCommand, BookingView],
    list_leads: OperatorContract[ListLeadsQuery, LeadListView],
    update_lead_status: OperatorContract[UpdateLeadStatusCommand, LeadView],
    list_handoffs: OperatorContract[ListHandoffsQuery, HandoffListView],
    resolve_handoff: OperatorContract[ResolveHandoffCommand, HandoffListItem],
    list_unanswered_questions: OperatorContract[
        ListUnansweredQuestionsQuery, UnansweredQuestionListView
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
    and staff, owner only where noted) plus the public Google OAuth callback,
    which sends the owner back to the cabinet (CABINET_BASE_URL).
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
            )
        )

    @router.get(f"{BUSINESS_PREFIX}/bookings")
    def get_bookings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        date_from: Annotated[str | None, Query(alias="from")] = None,
        date_to: Annotated[str | None, Query(alias="to")] = None,
        status: OptionalQuery = None,
        include_sandbox: OptionalQuery = None,
    ) -> BookingListView:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_bookings.operate(
            ListBookingsQuery(
                business_id=business.id,
                actor_id=user_id,
                date_from=parse_optional_text(date_from, LocalDate, "from"),
                date_to=parse_optional_text(date_to, LocalDate, "to"),
                status=parse_optional_text(status, BookingStatus, "status"),
                include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
            )
        )

    @router.post(f"{BUSINESS_PREFIX}/bookings", status_code=201)
    def post_booking(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            ManualBookingRequest, Depends(json_body_reader(ManualBookingRequest))
        ],
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

    @router.post(f"{BUSINESS_PREFIX}/bookings/{{booking_id}}/reschedule")
    def post_booking_reschedule(
        business_id: str,
        booking_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            RescheduleBookingRequest,
            Depends(json_body_reader(RescheduleBookingRequest)),
        ],
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

    @router.patch(f"{BUSINESS_PREFIX}/bookings/{{booking_id}}")
    def patch_booking(
        business_id: str,
        booking_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            UpdateBookingStatusRequest,
            Depends(json_body_reader(UpdateBookingStatusRequest)),
        ],
    ) -> BookingView:
        business: BusinessDocument = authorize(user_id, business_id)
        return update_booking_status.operate(
            UpdateBookingStatusCommand(
                business_id=business.id,
                actor_id=user_id,
                booking_id=parse_path_id(booking_id, BookingId, "Booking"),
                status=body.status,
            )
        )

    @router.get(f"{BUSINESS_PREFIX}/leads")
    def get_leads(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        status: OptionalQuery = None,
        include_sandbox: OptionalQuery = None,
    ) -> LeadListView:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_leads.operate(
            ListLeadsQuery(
                business_id=business.id,
                actor_id=user_id,
                status=parse_optional_text(status, LeadStatus, "status"),
                include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
            )
        )

    @router.patch(f"{BUSINESS_PREFIX}/leads/{{lead_id}}")
    def patch_lead(
        business_id: str,
        lead_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            UpdateLeadStatusRequest, Depends(json_body_reader(UpdateLeadStatusRequest))
        ],
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
        include_sandbox: OptionalQuery = None,
    ) -> HandoffListView:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_handoffs.operate(
            ListHandoffsQuery(
                business_id=business.id,
                actor_id=user_id,
                status=parse_optional_text(status, HandoffStatus, "status"),
                include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
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
    ) -> UnansweredQuestionListView:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_unanswered_questions.operate(
            ListUnansweredQuestionsQuery(
                business_id=business.id,
                include_resolved=parse_flag(include_resolved, "include_resolved"),
                include_sandbox=parse_flag(include_sandbox, "include_sandbox"),
            )
        )

    @router.post(f"{BUSINESS_PREFIX}/unanswered-questions/{{question_id}}/answer")
    def post_unanswered_question_answer(
        business_id: str,
        question_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            AnswerUnansweredQuestionRequest,
            Depends(json_body_reader(AnswerUnansweredQuestionRequest)),
        ],
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
                    "Back to the cabinet: /b/{business_id}/channels?calendar="
                    "connected, or ?calendar=error&reason=<reason>."
                )
            }
        },
    )
    def get_google_calendar_callback(
        code: OptionalQuery = None,
        state: OptionalQuery = None,
        error: OptionalQuery = None,
    ) -> Response:
        outcome: CalendarConnectionOutcome = complete_calendar_connection.operate(
            CompleteCalendarConnectionCommand(
                state=read_callback_value(state, CalendarAuthorizationState),
                code=read_callback_value(code, CalendarAuthorizationCode),
                provider_error=read_callback_value(error, CalendarProviderErrorCode),
            )
        )
        if cabinet_base_url is None:
            return render_calendar_outcome_page(outcome)

        return RedirectResponse(
            str(build_calendar_return_url(cabinet_base_url, outcome)),
            status_code=status.HTTP_303_SEE_OTHER,
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


def read_callback_value[Value: str](
    raw_value: str | None,
    value_type: Callable[[str], Value],
) -> Value | None:
    """A value of Google's callback query; blank means absent."""

    if raw_value is None or raw_value.strip() == "":
        return None

    return value_type(raw_value.strip()[:MAX_CALLBACK_VALUE_LENGTH])


def render_calendar_outcome_page(outcome: CalendarConnectionOutcome) -> HTMLResponse:
    """
    A plain page for the end of Google's consent when CABINET_BASE_URL is
    not configured (the owner returns to the cabinet by hand).
    """

    is_connected: bool = outcome.failure is None and outcome.connection is not None
    message: str = (
        "Google Calendar is connected. You can close this tab and return to "
        "the cabinet."
        if is_connected
        else "Google Calendar was not connected ("
        + (outcome.failure.value if outcome.failure is not None else "error")
        + "). Return to the cabinet and try again."
    )
    return HTMLResponse(
        content=(
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>Google Calendar</title></head>"
            f"<body><p>{message}</p></body></html>"
        ),
        status_code=(
            status.HTTP_200_OK if is_connected else status.HTTP_400_BAD_REQUEST
        ),
        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"},
    )


def json_body_reader[Body: BaseModel](
    body_type: type[Body],
) -> Callable[[Request], Awaitable[Body]]:
    """
    FastAPI dependency that validates the raw JSON body in JSON mode (strict
    DTOs accept enum values and typed strings in their wire form there).
    """

    async def read_json_body(request: Request) -> Body:
        raw_body: bytes = await request.body()
        try:
            return body_type.model_validate_json(raw_body)
        except ValidationError as error:
            details: str = "; ".join(
                f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                for item in error.errors()
            )
            raise ValidationFailedError(f"Invalid request body: {details}") from error

    return read_json_body


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
    if raw_value is None or raw_value == "":
        return False

    normalized: str = raw_value.strip().lower()
    if normalized in TRUE_QUERY_VALUES:
        return True

    if normalized in FALSE_QUERY_VALUES:
        return False

    raise ValidationFailedError(f"Invalid {name}: {raw_value!r} (use true or false).")
