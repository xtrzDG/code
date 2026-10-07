"""Cabinet route of the dashboard."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.operations.business_access import (
    BUSINESS_PREFIX,
    BusinessAuthorizer,
)
from app.gateways.http.operations.query_values import parse_optional_text
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.operations.dashboard import DashboardStats, DashboardStatsQuery
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.users.prefixed_id import UserId


def build_dashboard_routes(
    *,
    current_user: CurrentUserDependency,
    authorize: BusinessAuthorizer,
    get_dashboard_stats: OperatorContract[DashboardStatsQuery, DashboardStats],
) -> APIRouter:
    """The dashboard of a business (Bearer auth; owners and staff)."""

    router = APIRouter()

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
                user_id=user_id,
                business_id=business.id,
                date_from=parse_optional_text(date_from, LocalDate, "from"),
                date_to=parse_optional_text(date_to, LocalDate, "to"),
            )
        )

    return router
