"""Cabinet HTTP API of the operations module: availability, bookings, leads,
handoffs, unanswered questions, dashboard and Google Calendar.

Path and query parameters arrive as raw strings and are converted to typed
primitives here (the transport boundary). JSON bodies are validated in JSON
mode, so enum values and typed strings parse strictly from their wire form,
and are described for OpenAPI so the cabinet's generated client knows them.
Lists are paged with `?limit=N&cursor=…`.
"""

from fastapi import APIRouter

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.idempotency.idempotency_dependency import (
    NO_IDEMPOTENCY,
    IdempotencyDependency,
)
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.operations.booking_routes import build_booking_routes
from app.gateways.http.operations.business_access import build_business_authorizer
from app.gateways.http.operations.dashboard_routes import build_dashboard_routes
from app.gateways.http.operations.follow_up_routes import build_follow_up_routes
from app.gateways.http.operations.google_calendar_routes import (
    build_google_calendar_routes,
)
from app.gateways.http.user_authentication import CurrentUserDependency
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
from app.schemas.dto.operations.bookings import (
    BookingPage,
    ListBookingsQuery,
    ManualBookingCommand,
    RevertBookingStatusCommand,
    UpdateBookingCommand,
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
    ReopenHandoffCommand,
    ResolveHandoffCommand,
)
from app.schemas.dto.operations.leads import (
    LeadPage,
    ListLeadsQuery,
    UpdateLeadStatusCommand,
)
from app.schemas.dto.operations.unanswered_questions import (
    AnsweredQuestionResult,
    AnswerUnansweredQuestionCommand,
    ListUnansweredQuestionsQuery,
    UnansweredQuestionPage,
)
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl


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
    revert_booking_status: OperatorContract[RevertBookingStatusCommand, BookingView],
    list_leads: OperatorContract[ListLeadsQuery, LeadPage],
    update_lead_status: OperatorContract[UpdateLeadStatusCommand, LeadView],
    list_handoffs: OperatorContract[ListHandoffsQuery, HandoffPage],
    resolve_handoff: OperatorContract[ResolveHandoffCommand, HandoffListItem],
    reopen_handoff: OperatorContract[ReopenHandoffCommand, HandoffListItem],
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
    idempotent: IdempotencyDependency = NO_IDEMPOTENCY,
) -> APIRouter:
    """
    Cabinet routes under /v1/businesses/{business_id} (Bearer auth; owners
    and staff, owner only where noted) plus the Google OAuth callback: the
    public callback only forwards Google's values to the cabinet
    (CABINET_BASE_URL), which finishes connecting for the signed-in owner
    through the authenticated completion route.
    """

    authorize = build_business_authorizer(authorize_business_access)
    router = APIRouter(tags=["operations"], responses=standard_error_responses())
    router.include_router(
        build_booking_routes(
            current_user=current_user,
            authorize=authorize,
            check_availability=check_availability,
            list_bookings=list_bookings,
            create_manual_booking=create_manual_booking,
            cancel_booking=cancel_booking,
            reschedule_booking=reschedule_booking,
            update_booking=update_booking,
            revert_booking_status=revert_booking_status,
            idempotent=idempotent,
        )
    )
    router.include_router(
        build_follow_up_routes(
            current_user=current_user,
            authorize=authorize,
            list_leads=list_leads,
            update_lead_status=update_lead_status,
            list_handoffs=list_handoffs,
            resolve_handoff=resolve_handoff,
            reopen_handoff=reopen_handoff,
            list_unanswered_questions=list_unanswered_questions,
            answer_unanswered_question=answer_unanswered_question,
        )
    )
    router.include_router(
        build_dashboard_routes(
            current_user=current_user,
            authorize=authorize,
            get_dashboard_stats=get_dashboard_stats,
        )
    )
    router.include_router(
        build_google_calendar_routes(
            current_user=current_user,
            authorize=authorize,
            start_calendar_connection=start_calendar_connection,
            complete_calendar_connection=complete_calendar_connection,
            disconnect_calendar=disconnect_calendar,
            get_calendar_connection=get_calendar_connection,
            cabinet_base_url=cabinet_base_url,
        )
    )
    return router
