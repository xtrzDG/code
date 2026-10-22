"""The card on file of a business and the Stripe payment webhook."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.billing_routes import (
    PaymentWebhookOperator,
    parse_business_id,
    parse_optional_language,
)
from app.gateways.http.idempotency.idempotency_dependency import (
    NO_IDEMPOTENCY,
    IdempotencyDependency,
)
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    read_raw_request_body,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.payments import PaymentProvider
from app.schemas.dto.payment_methods import (
    CardSetupSessionView,
    PaymentMethodQuery,
    PaymentMethodView,
    StartCardSetupCommand,
    StartCardSetupRequest,
)
from app.schemas.dto.payments import PaymentWebhookDelivery, PaymentWebhookReceipt
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.strings import (
    PaymentWebhookBody,
    PaymentWebhookSignature,
)
from app.schemas.typings.users.prefixed_id import UserId

STRIPE_WEBHOOK_PATH: str = "/v1/payments/stripe/webhook"
PAYMENT_METHOD_PATH: str = "/v1/businesses/{business_id}/billing/payment-method"

type PaymentMethodOperator = OperatorContract[PaymentMethodQuery, PaymentMethodView]
type StartCardSetupOperator = OperatorContract[
    StartCardSetupCommand, CardSetupSessionView
]
read_card_setup_body = build_json_body_dependency(StartCardSetupRequest, optional=True)


def build_payment_method_router(
    get_payment_method_operator: PaymentMethodOperator,
    start_card_setup_operator: StartCardSetupOperator,
    payment_webhook_operator: PaymentWebhookOperator,
    current_user: CurrentUserDependency,
    idempotent: IdempotencyDependency = NO_IDEMPOTENCY,
) -> APIRouter:
    """
    Routes (cabinet routes need a bearer token of a business owner):
        GET  /v1/businesses/{business_id}/billing/payment-method   card on file
        POST /v1/businesses/{business_id}/billing/payment-method   page that
             saves or replaces the card ("Save card", "Update card"; 201)
        POST /v1/payments/stripe/webhook                           Stripe event

    The card on file shows the card's brand, last four digits and expiry,
    who charges it, the trial's "Save card" prompt (from day 10) and where
    the retries of a declined charge stand. Saving a card charges nothing
    now; 409 when no card can be saved (an unpaid bill is paid instead).
    The webhook needs no token: its `Stripe-Signature` is verified (403
    when wrong, stale or Stripe is not configured), and it answers 200 for
    applied, repeated and ignored events, 404 for an unknown order and 422
    for a malformed body.
    """

    router = APIRouter(tags=["billing"], responses=standard_error_responses())

    @router.get(PAYMENT_METHOD_PATH)
    def get_payment_method(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> PaymentMethodView:
        return get_payment_method_operator.operate(
            PaymentMethodQuery(
                user_id=user_id, business_id=parse_business_id(business_id)
            )
        )

    @router.post(
        PAYMENT_METHOD_PATH,
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(StartCardSetupRequest, optional=True),
        dependencies=[Depends(idempotent)],
    )
    def start_card_setup(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[StartCardSetupRequest, Depends(read_card_setup_body)],
        language: str | None = None,
    ) -> CardSetupSessionView:
        return start_card_setup_operator.operate(
            StartCardSetupCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
                display_language=parse_optional_language(language),
            )
        )

    @router.post(STRIPE_WEBHOOK_PATH, tags=["payments"])
    def receive_stripe_webhook(
        raw_body: Annotated[bytes, Depends(read_raw_request_body)],
        stripe_signature: Annotated[str | None, Header()] = None,
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
                provider=PaymentProvider.STRIPE,
                signature=(
                    None
                    if stripe_signature is None or stripe_signature.strip() == ""
                    else PaymentWebhookSignature(stripe_signature)
                ),
            )
        )

    return router
