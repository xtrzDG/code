"""Billing: why owners cancel, the offers instead, the seasonal pause."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.billing_routes import (
    parse_business_id,
    parse_optional_language,
)
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.billing_cabinet import BillingOverview
from app.schemas.dto.subscription_lifecycle import (
    AcceptRetentionOfferCommand,
    AcceptRetentionOfferRequest,
    PauseSubscriptionCommand,
    PauseSubscriptionRequest,
    ResumeSubscriptionCommand,
    SubscriptionLifecycleQuery,
    SubscriptionLifecycleView,
)
from app.schemas.typings.users.prefixed_id import UserId

type SubscriptionLifecycleOperator = OperatorContract[
    SubscriptionLifecycleQuery, SubscriptionLifecycleView
]
type PauseSubscriptionOperator = OperatorContract[
    PauseSubscriptionCommand, BillingOverview
]
type ResumeSubscriptionOperator = OperatorContract[
    ResumeSubscriptionCommand, BillingOverview
]
type AcceptRetentionOfferOperator = OperatorContract[
    AcceptRetentionOfferCommand, BillingOverview
]
read_pause_body = build_json_body_dependency(PauseSubscriptionRequest)
read_offer_body = build_json_body_dependency(AcceptRetentionOfferRequest)


def build_billing_lifecycle_router(
    get_subscription_lifecycle_operator: SubscriptionLifecycleOperator,
    pause_subscription_operator: PauseSubscriptionOperator,
    resume_subscription_operator: ResumeSubscriptionOperator,
    accept_retention_offer_operator: AcceptRetentionOfferOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (a bearer token of a business owner):
        GET  /v1/businesses/{business_id}/billing/lifecycle?language=
             the cancel dialog's offer per reason and the pause card
        POST /v1/businesses/{business_id}/billing/pause          pause
        POST /v1/businesses/{business_id}/billing/resume         resume
        POST /v1/businesses/{business_id}/billing/offers/accept  take an offer

    The POST routes answer with the billing page. A pause the business
    cannot take now, an offer that is not the one its reason gets, or a
    resume without a pause is refused with 409.
    """

    router = APIRouter(tags=["billing"], responses=standard_error_responses())

    @router.get("/v1/businesses/{business_id}/billing/lifecycle")
    def get_subscription_lifecycle(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: str | None = None,
    ) -> SubscriptionLifecycleView:
        return get_subscription_lifecycle_operator.operate(
            SubscriptionLifecycleQuery(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                display_language=parse_optional_language(language),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/billing/pause",
        openapi_extra=describe_json_body(PauseSubscriptionRequest),
    )
    def pause_subscription(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[PauseSubscriptionRequest, Depends(read_pause_body)],
        language: str | None = None,
    ) -> BillingOverview:
        return pause_subscription_operator.operate(
            PauseSubscriptionCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
                display_language=parse_optional_language(language),
            )
        )

    @router.post("/v1/businesses/{business_id}/billing/resume")
    def resume_subscription(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: str | None = None,
    ) -> BillingOverview:
        return resume_subscription_operator.operate(
            ResumeSubscriptionCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                display_language=parse_optional_language(language),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/billing/offers/accept",
        openapi_extra=describe_json_body(AcceptRetentionOfferRequest),
    )
    def accept_retention_offer(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AcceptRetentionOfferRequest, Depends(read_offer_body)],
        language: str | None = None,
    ) -> BillingOverview:
        return accept_retention_offer_operator.operate(
            AcceptRetentionOfferCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
                display_language=parse_optional_language(language),
            )
        )

    return router
