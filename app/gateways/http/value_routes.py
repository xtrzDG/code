"""
Cabinet routes of what the assistant is worth: the value of a period, the
average check, the owner's digest choices, the stored reports and today's
queue.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.value import ValuePeriod, ValueReportKind
from app.schemas.dto.value.value_model import ValueModel
from app.schemas.dto.value.value_reports import (
    ValueReportPage,
    ValueReportPageQuery,
    ValueReportQuery,
    ValueReportView,
)
from app.schemas.dto.value.value_views import (
    BusinessValueQuery,
    DigestPreferencesQuery,
    DigestPreferencesRequest,
    DigestPreferencesView,
    TodayQueue,
    TodayQueueQuery,
    UpdateDigestPreferencesCommand,
    UpdateValueSettingsCommand,
    ValueSettingsQuery,
    ValueSettingsRequest,
    ValueSettingsView,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.value.prefixed_id import ValueReportId

B: str = "/v1/businesses/{business_id}"

read_value_settings_body = build_json_body_dependency(ValueSettingsRequest)
read_digest_preferences_body = build_json_body_dependency(DigestPreferencesRequest)


def build_value_router(
    *,
    current_user: CurrentUserDependency,
    get_value: OperatorContract[BusinessValueQuery, ValueModel],
    get_settings: OperatorContract[ValueSettingsQuery, ValueSettingsView],
    update_settings: OperatorContract[UpdateValueSettingsCommand, ValueSettingsView],
    get_preferences: OperatorContract[DigestPreferencesQuery, DigestPreferencesView],
    update_preferences: OperatorContract[
        UpdateDigestPreferencesCommand, DigestPreferencesView
    ],
    list_reports: OperatorContract[ValueReportPageQuery, ValueReportPage],
    get_report: OperatorContract[ValueReportQuery, ValueReportView],
    get_today_queue: OperatorContract[TodayQueueQuery, TodayQueue],
) -> APIRouter:
    """
    Routes (Bearer auth; owners and staff where noted, else owners):
        GET {B}/value                   value of a period (staff: no money)
        GET {B}/value/settings          the average check
        PUT {B}/value/settings          set or clear it
        GET {B}/digest-preferences      the signed-in owner's summaries
        PUT {B}/digest-preferences      turn them on or off
        GET {B}/value-reports           stored reports of a kind (paged)
        GET {B}/value-reports/{id}      one stored report
        GET {B}/today-queue             today's bookings (owners and staff)
    """

    router = APIRouter(tags=["value"], responses=standard_error_responses())

    def business(raw_id: str) -> BusinessId:
        return parse_path_identifier(raw_id, BusinessId, "Business")

    @router.get(f"{B}/value")
    def get_business_value(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        period: Annotated[str | None, Query()] = None,
        date_from: Annotated[str | None, Query(alias="from")] = None,
        date_to: Annotated[str | None, Query(alias="to")] = None,
    ) -> ValueModel:
        """
        `period`: today, 7d, 30d, 90d, last_week or last_month; or local
        dates `from` and `to`; compared with the period before.
        """

        return get_value.operate(
            BusinessValueQuery(
                user_id=user_id,
                business_id=business(business_id),
                period=parse_optional(period, ValuePeriod, "period"),
                date_from=parse_optional(date_from, LocalDate, "from"),
                date_to=parse_optional(date_to, LocalDate, "to"),
            )
        )

    @router.get(f"{B}/value/settings")
    def get_value_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ValueSettingsView:
        return get_settings.operate(
            ValueSettingsQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.put(
        f"{B}/value/settings",
        openapi_extra=describe_json_body(ValueSettingsRequest),
    )
    def update_value_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ValueSettingsRequest, Depends(read_value_settings_body)],
    ) -> ValueSettingsView:
        return update_settings.operate(
            UpdateValueSettingsCommand(
                user_id=user_id, business_id=business(business_id), request=body
            )
        )

    @router.get(f"{B}/digest-preferences")
    def get_digest_preferences(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> DigestPreferencesView:
        return get_preferences.operate(
            DigestPreferencesQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.put(
        f"{B}/digest-preferences",
        openapi_extra=describe_json_body(DigestPreferencesRequest),
    )
    def update_digest_preferences(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[
            DigestPreferencesRequest, Depends(read_digest_preferences_body)
        ],
    ) -> DigestPreferencesView:
        return update_preferences.operate(
            UpdateDigestPreferencesCommand(
                user_id=user_id, business_id=business(business_id), request=body
            )
        )

    @router.get(f"{B}/value-reports")
    def list_value_reports(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        kind: Annotated[str | None, Query()] = None,
        limit: Annotated[str | None, Query()] = None,
        cursor: Annotated[str | None, Query()] = None,
    ) -> ValueReportPage:
        """`kind`: monthly (default), weekly or daily."""

        return list_reports.operate(
            ValueReportPageQuery(
                user_id=user_id,
                business_id=business(business_id),
                kind=parse_optional(kind, ValueReportKind, "kind")
                or ValueReportKind.MONTHLY,
                page=parse_page_request(limit, cursor),
            )
        )

    @router.get(f"{B}/value-reports/{{report_id}}")
    def get_value_report(
        business_id: str,
        report_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ValueReportView:
        return get_report.operate(
            ValueReportQuery(
                user_id=user_id,
                business_id=business(business_id),
                report_id=parse_path_identifier(report_id, ValueReportId, "Report"),
            )
        )

    @router.get(f"{B}/today-queue")
    def get_today_queue_route(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> TodayQueue:
        """Today's bookings: on, still to start, waiting for confirmation."""

        return get_today_queue.operate(
            TodayQueueQuery(user_id=user_id, business_id=business(business_id))
        )

    return router
