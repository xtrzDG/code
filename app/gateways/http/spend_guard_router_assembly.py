"""
The spend guard's routes and route parts: the allowed chat websites, the
admin's spend, the widget's origin check and the generic request limits.
"""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.admin_spend_routes import build_admin_spend_router
from app.gateways.http.middleware.anonymous_request_limit_middleware import (
    AdmitRequest,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.gateways.http.widget_origin_guard import (
    WidgetOriginGuard,
    build_widget_origin_guard,
)
from app.gateways.http.widget_origin_routes import build_widget_origin_router


def build_spend_guard_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    spend_guard = operators.spend_guard
    return [
        build_widget_origin_router(
            current_user=current_user,
            get_allowed_origins=spend_guard.get_widget_allowed_origins_operator(),
            save_allowed_origins=spend_guard.save_widget_allowed_origins_operator(),
        ),
        build_admin_spend_router(
            current_user=current_user,
            get_platform_spend=spend_guard.get_platform_spend_operator(),
            set_business_spend_limits=spend_guard.set_business_spend_limits_operator(),
        ),
    ]


def widget_origin_guard_of(operators: OperatorsContainer) -> WidgetOriginGuard:
    """The website chat routes' check of the page they were called from."""

    return build_widget_origin_guard(
        operators.spend_guard.check_widget_origin_operator()
    )


def anonymous_request_admission_of(operators: OperatorsContainer) -> AdmitRequest:
    """The per-address limit of requests without a token (the middleware's)."""

    return operators.spend_guard.admit_api_request_operator().operate
