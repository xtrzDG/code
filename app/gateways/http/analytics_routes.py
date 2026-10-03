"""Growth analytics: the founder's metrics and the cabinet's telemetry."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.analytics.admin_metrics_query import AdminMetricsQuery
from app.schemas.dto.analytics.admin_metrics_view import AdminMetricsView
from app.schemas.dto.analytics.telemetry import (
    TelemetryBatchCommand,
    TelemetryBatchReceipt,
    TelemetryBatchRequest,
)
from app.schemas.typings.analytics.constrained_strings import (
    AcquisitionSourceKey,
    MetricsDate,
)
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.users.prefixed_id import UserId

type GetAdminMetricsOperator = OperatorContract[AdminMetricsQuery, AdminMetricsView]
type RecordTelemetryOperator = OperatorContract[
    TelemetryBatchCommand,
    TelemetryBatchReceipt,
]

read_telemetry_body = build_json_body_dependency(TelemetryBatchRequest)


def build_analytics_router(
    get_admin_metrics_operator: GetAdminMetricsOperator,
    record_telemetry_operator: RecordTelemetryOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token):
        GET  /v1/admin/metrics          the founder's growth metrics: funnel,
             ?from=&to=&country=        tunnel, activation, trial to paid,
             &niche=&source=            MRR movements in euros, margin,
                                        cohorts, sources, Web Vitals
                                        (platform admins; others get 403)
        POST /v1/telemetry/events       up to 50 cabinet reports (Web Vitals,
                                        tunnel steps); 202, or 429 past 30
                                        batches a minute
    """

    router = APIRouter(tags=["analytics"], responses=standard_error_responses())

    @router.get("/v1/admin/metrics")
    def get_admin_metrics(
        user_id: Annotated[UserId, Depends(current_user)],
        date_from: Annotated[str | None, Query(alias="from")] = None,
        date_to: Annotated[str | None, Query(alias="to")] = None,
        country: str | None = None,
        niche: str | None = None,
        source: str | None = None,
    ) -> AdminMetricsView:
        return get_admin_metrics_operator.operate(
            AdminMetricsQuery(
                user_id=user_id,
                period_start=parse_optional(date_from, MetricsDate, "from"),
                period_end=parse_optional(date_to, MetricsDate, "to"),
                country_code=parse_optional(
                    None if country is None else country.strip().upper(),
                    CountryCode,
                    "country",
                ),
                niche_key=parse_optional(niche, NicheKey, "niche"),
                source=parse_optional(
                    None if source is None else source.strip().lower(),
                    AcquisitionSourceKey,
                    "source",
                ),
            )
        )

    @router.post(
        "/v1/telemetry/events",
        status_code=status.HTTP_202_ACCEPTED,
        openapi_extra=describe_json_body(TelemetryBatchRequest),
    )
    def record_telemetry(
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[TelemetryBatchRequest, Depends(read_telemetry_body)],
    ) -> TelemetryBatchReceipt:
        return record_telemetry_operator.operate(
            TelemetryBatchCommand(user_id=user_id, events=body.events)
        )

    return router
