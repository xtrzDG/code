"""
The website chat's origin check as a route dependency: before a widget
route runs, the page its request came from (Origin, else Referer) must be
one the business allows (`CheckWidgetOriginUseCase`; 403 otherwise, with
the widget's CORS headers like every widget answer).
"""

from collections.abc import Callable

from fastapi import Request

from app.contracts.operator_contract import OperatorContract
from app.schemas.dto.widget_origins import WidgetOriginCheck
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.spend.widget_origins import page_origin_of

type WidgetOriginGuard = Callable[[Request, str], None]


def build_widget_origin_guard(
    check_widget_origin_operator: OperatorContract[WidgetOriginCheck, None],
) -> WidgetOriginGuard:
    """A dependency of the routes under /v1/widget/{business_id}/."""

    def require_allowed_origin(request: Request, business_id: str) -> None:
        try:
            checked_business = BusinessId(business_id)
        except ValueError, TypeError:
            return  # The route itself answers an unknown chat with 404.

        check_widget_origin_operator.operate(
            WidgetOriginCheck(
                business_id=checked_business,
                page_origin=page_origin_of(
                    request.headers.get("origin"), request.headers.get("referer")
                ),
            )
        )

    return require_allowed_origin
