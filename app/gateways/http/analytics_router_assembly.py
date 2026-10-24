"""Router of the growth analytics: the founder's metrics, cabinet telemetry."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.analytics_routes import build_analytics_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_analytics_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """GET /v1/admin/metrics and POST /v1/telemetry/events."""

    analytics = operators.analytics
    return [
        build_analytics_router(
            get_admin_metrics_operator=analytics.get_admin_metrics_operator(),
            record_telemetry_operator=analytics.record_telemetry_operator(),
            current_user=current_user,
        )
    ]
