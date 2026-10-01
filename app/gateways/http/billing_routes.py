"""Billing: subscription, invoices, checkout and the Flitt payment webhook."""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request, status
from pydantic import BaseModel, ValidationError

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.strict_request_parsing import (
    describe_json_body,
    describe_validation_error,
    parse_path_identifier,
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
)
from app.schemas.dto.payments import PaymentWebhookDelivery, PaymentWebhookReceipt
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
type PaymentWebhookOperator = OperatorContract[
    PaymentWebhookDelivery,
    PaymentWebhookReceipt,
]
type OptionalJsonBodyDependency[Body: BaseModel] = Callable[
    [Request],
    Coroutine[Any, Any, Body],
]


def build_optional_json_body_dependency[Body: BaseModel](
    body_type: type[Body],
) -> OptionalJsonBodyDependency[Body]:
    """
    Parse a JSON body whose fields are all optional; an empty body means
    the defaults. Invalid bodies become ValidationFailedError (HTTP 422).
    """

    async def read_optional_json_body(request: Request) -> Body:
        raw_body: bytes = await request.body()
        try:
            return body_type.model_validate_json(raw_body.strip() or b"{}")
        except ValidationError as error:
            raise ValidationFailedError(describe_validation_error(error)) from error

    return read_optional_json_body


async def read_raw_body(request: Request) -> bytes:
    """The request body exactly as sent (signatures cover the raw values)."""

    return await request.body()


read_start_trial_body = build_optional_json_body_dependency(StartTrialRequest)
read_change_plan_body = build_optional_json_body_dependency(ChangePlanRequest)
read_start_checkout_body = build_optional_json_body_dependency(StartCheckoutRequest)


def build_billing_router(
    get_billing_overview_operator: BillingOverviewOperator,
    start_trial_operator: StartTrialOperator,
    change_plan_operator: ChangePlanOperator,
    cancel_subscription_operator: CancelSubscriptionOperator,
    start_checkout_operator: StartCheckoutOperator,
    payment_webhook_operator: PaymentWebhookOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (cabinet routes need a bearer token of a business owner):
        GET  /v1/businesses/{business_id}/billing?language=   billing page
        POST /v1/businesses/{business_id}/billing/trial      start trial (201)
        POST /v1/businesses/{business_id}/billing/plan       change plan
        POST /v1/businesses/{business_id}/billing/cancel     cancel
        POST /v1/businesses/{business_id}/billing/checkout   payment page (201)
        POST /v1/payments/flitt/webhook                      Flitt callback

    `language` is a BCP 47 tag; it defaults to the owner language of the
    business. The webhook needs no token: its signature is verified, and it
    answers 200 for applied, repeated and ignored notifications, 403 for a
    wrong signature, 404 for an unknown order and 422 for a malformed body.
    """

    router = APIRouter(tags=["billing"])

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
        openapi_extra=describe_json_body(StartTrialRequest),
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
        openapi_extra=describe_json_body(ChangePlanRequest),
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

    @router.post("/v1/businesses/{business_id}/billing/cancel")
    def cancel_subscription(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: str | None = None,
    ) -> BillingOverview:
        return cancel_subscription_operator.operate(
            CancelSubscriptionCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                display_language=parse_optional_language(language),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/billing/checkout",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(StartCheckoutRequest),
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

    @router.post(FLITT_WEBHOOK_PATH, tags=["payments"])
    def receive_flitt_webhook(
        raw_body: Annotated[bytes, Depends(read_raw_body)],
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
