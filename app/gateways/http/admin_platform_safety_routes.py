"""
The platform's brakes and the daily payment reconciliation, for the
platform admin (Bearer auth, a two-factor session).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.payment_reconciliation import (
    PaymentReconciliationQuery,
    PaymentReconciliationView,
)
from app.schemas.dto.platform_pause import (
    PlatformPauseCommand,
    PlatformPauseQuery,
    PlatformPauseRequest,
    PlatformPauseView,
)
from app.schemas.typings.users.prefixed_id import UserId

PLATFORM_PAUSE_PATH: str = "/v1/admin/platform/pause"
read_pause_body = build_json_body_dependency(PlatformPauseRequest)


def build_admin_platform_safety_router(
    *,
    current_user: CurrentUserDependency,
    get_platform_pause: OperatorContract[PlatformPauseQuery, PlatformPauseView],
    set_platform_pause: OperatorContract[PlatformPauseCommand, PlatformPauseView],
    get_payment_reconciliation: OperatorContract[
        PaymentReconciliationQuery, PaymentReconciliationView
    ],
) -> APIRouter:
    """
    Routes:
        GET /v1/admin/platform/pause
            whether every assistant is paused (who, when, why) and how the
            daily budget stop stands; admins who see operations
        PUT /v1/admin/platform/pause
            pause (`is_paused: true`) or resume every assistant at once,
            with a reason; SUPER admins after a recent sign-in (401
            step_up_required), audited on the platform's log; 409 when it
            already stands so
        GET /v1/admin/payments/reconciliation
            the latest daily reconciliation of payments with Flitt and
            Stripe and its mismatches; SUPER and BILLING admins
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get(PLATFORM_PAUSE_PATH)
    def get_admin_platform_pause(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> PlatformPauseView:
        return get_platform_pause.operate(PlatformPauseQuery(user_id=user_id))

    @router.put(
        PLATFORM_PAUSE_PATH, openapi_extra=describe_json_body(PlatformPauseRequest)
    )
    def set_admin_platform_pause(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[PlatformPauseRequest, Depends(read_pause_body)],
    ) -> PlatformPauseView:
        return set_platform_pause.operate(
            PlatformPauseCommand(
                user_id=user_id,
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get("/v1/admin/payments/reconciliation")
    def get_admin_payment_reconciliation(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> PaymentReconciliationView:
        return get_payment_reconciliation.operate(
            PaymentReconciliationQuery(user_id=user_id)
        )

    return router
