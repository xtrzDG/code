"""Billing: subscription, invoices, checkout and the Flitt payment webhook."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.idempotency.idempotency_dependency import (
    NO_IDEMPOTENCY,
    IdempotencyDependency,
)
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_raw_request_body,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    BillingOverviewQuery,
    CancelSubscriptionCommand,
    ChangePlanCommand,
    ChangePlanRequest,
    CheckoutSessionView,
    StartCheckoutCommand,
    StartCheckoutRequest,
    StartTrialCommand,
    StartTrialRequest,
    SubscribeCommand,
    SubscribeRequest,
)
from app.schemas.dto.payments import PaymentWebhookDelivery, PaymentWebhookReceipt
from app.schemas.dto.subscription_lifecycle import CancelSubscriptionRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.strings import (
    PaymentWebhookBody,
    PaymentWebhookContentType,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.localization.language_tags import parse_language_tag

FLITT_WEBHOOK_PATH: str = "/v1/payments/flitt/webhook"

type BillingOverviewOperator = OperatorContract[BillingOverviewQuery, BillingOverview]
type StartTrialOperator = OperatorContract[StartTrialCommand, BillingOverview]
type ChangePlanOperator = OperatorContract[ChangePlanCommand, BillingOverview]
type CancelSubscriptionOperator = OperatorContract[
    CancelSubscriptionCommand,
    BillingOverview,
]
type StartCheckoutOperator = OperatorContract[StartCheckoutCommand, CheckoutSessionView]
type SubscribeOperator = OperatorContract[SubscribeCommand, CheckoutSessionView]
type PaymentWebhookOperator = OperatorContract[
    PaymentWebhookDelivery,
    PaymentWebhookReceipt,
]
read_start_trial_body = build_json_body_dependency(StartTrialRequest, optional=True)
read_change_plan_body = build_json_body_dependency(ChangePlanRequest, optional=True)
read_start_checkout_body = build_json_body_dependency(
    StartCheckoutRequest,
    optional=True,
)
read_subscribe_body = build_json_body_dependency(SubscribeRequest)
read_cancel_body = build_json_body_dependency(CancelSubscriptionRequest, optional=True)


def build_billing_router(
    get_billing_overview_operator: BillingOverviewOperator,
    start_trial_operator: StartTrialOperator,
    change_plan_operator: ChangePlanOperator,
    cancel_subscription_operator: CancelSubscriptionOperator,
    start_checkout_operator: StartCheckoutOperator,
    subscribe_operator: SubscribeOperator,
    payment_webhook_operator: PaymentWebhookOperator,
    current_user: CurrentUserDependency,
    idempotent: IdempotencyDependency = NO_IDEMPOTENCY,
) -> APIRouter:
    """
    Routes (cabinet routes need a bearer token of a business owner):
        GET  /v1/businesses/{business_id}/billing?language=   billing page
        POST /v1/businesses/{business_id}/billing/trial      start trial (201)
        POST /v1/businesses/{business_id}/billing/plan       change plan
        POST /v1/businesses/{business_id}/billing/cancel     cancel (why: body)
        POST /v1/businesses/{business_id}/billing/checkout   payment page (201)
        POST /v1/businesses/{business_id}/billing/subscribe  plan + payment page
                                                             (201)
        POST /v1/payments/flitt/webhook                      Flitt callback

    `language` is a BCP 47 tag; it defaults to the owner language of the
    business. Subscribe works with or without a subscription (after the
    trial, after cancelling, or instead of the trial): it switches to the
    chosen plan and period and answers with the payment page like checkout.
    The webhook needs no token: its signature is verified, and it answers
    200 for applied, repeated and ignored notifications, 403 for a wrong
    signature, 404 for an unknown order and 422 for a malformed body.
    """

    router = APIRouter(tags=["billing"], responses=standard_error_responses())

    @router.get("/v1/businesses/{business_id}/billing")
    def get_billing_overview(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: str | None = None,
    ) -> BillingOverview:
        return get_billing_overview_operator.operate(
            BillingOverviewQuery(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                display_language=parse_optional_language(language),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/billing/trial",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(StartTrialRequest, optional=True),
    )
    def start_trial(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[StartTrialRequest, Depends(read_start_trial_body)],
        language: str | None = None,
    ) -> BillingOverview:
        return start_trial_operator.operate(
            StartTrialCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
                display_language=parse_optional_language(language),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/billing/plan",
        openapi_extra=describe_json_body(ChangePlanRequest, optional=True),
    )
    def change_plan(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ChangePlanRequest, Depends(read_change_plan_body)],
        language: str | None = None,
    ) -> BillingOverview:
        return change_plan_operator.operate(
            ChangePlanCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
                display_language=parse_optional_language(language),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/billing/cancel",
        openapi_extra=describe_json_body(CancelSubscriptionRequest, optional=True),
    )
    def cancel_subscription(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CancelSubscriptionRequest, Depends(read_cancel_body)],
        language: str | None = None,
    ) -> BillingOverview:
        return cancel_subscription_operator.operate(
            CancelSubscriptionCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
                display_language=parse_optional_language(language),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/billing/checkout",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(StartCheckoutRequest, optional=True),
        dependencies=[Depends(idempotent)],
    )
    def start_checkout(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[StartCheckoutRequest, Depends(read_start_checkout_body)],
        language: str | None = None,
    ) -> CheckoutSessionView:
        return start_checkout_operator.operate(
            StartCheckoutCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
                display_language=parse_optional_language(language),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/billing/subscribe",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(SubscribeRequest),
        dependencies=[Depends(idempotent)],
    )
    def subscribe(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[SubscribeRequest, Depends(read_subscribe_body)],
        language: str | None = None,
    ) -> CheckoutSessionView:
        return subscribe_operator.operate(
            SubscribeCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
                display_language=parse_optional_language(language),
            )
        )

    @router.post(FLITT_WEBHOOK_PATH, tags=["payments"])
    def receive_flitt_webhook(
        raw_body: Annotated[bytes, Depends(read_raw_request_body)],
        content_type: Annotated[str | None, Header()] = None,
    ) -> PaymentWebhookReceipt:
        try:
            body_text: str = raw_body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValidationFailedError(
                "Payment notification body is not UTF-8."
            ) from error

        return payment_webhook_operator.operate(
            PaymentWebhookDelivery(
                body=PaymentWebhookBody(body_text),
                content_type=(
                    None
                    if content_type is None
                    else PaymentWebhookContentType(content_type)
                ),
            )
        )

    return router


def parse_business_id(raw_business_id: str) -> BusinessId:
    return parse_path_identifier(raw_business_id, BusinessId, "Business")


def parse_optional_language(raw_language: str | None) -> LanguageTag | None:
    """BCP 47 tag from the query; raises UnsupportedLanguageError (422)."""

    if raw_language is None or raw_language.strip() == "":
        return None

    return parse_language_tag(raw_language)
