"""The Stripe billing adapter: pages, events without configuration, retries."""

import pytest

from app.adapters.payments.stripe_billing_adapter import StripeBillingAdapter
from app.schemas.constants.payments import (
    PaymentProvider,
    PaymentStatus,
)
from app.schemas.dto.payment_retries import PaymentRetryRequest
from app.schemas.dto.payments import (
    PaymentWebhookDelivery,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import (
    PaymentRetryAttempt,
)
from app.schemas.typings.billing.prefixed_id import InvoiceId, PaymentOrderId
from app.schemas.typings.billing.strings import (
    InvoiceDescription,
    PaymentProviderReference,
    PaymentWebhookBody,
    PaymentWebhookSignature,
)
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
)
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.utilities.billing.payment_retry_identity import derive_payment_retry_id
from tests.billing.billing_fakes import AdjustableClock
from tests.billing.billing_settings import (
    CABINET_ORIGIN,
)
from tests.billing.stripe_sandbox import StripeSandbox
from tests.payments.stripe_requests import (
    DAY_SECONDS,
    build_stripe_client,
    checkout_request,
    euros,
)


def build_adapter(
    sandbox: StripeSandbox | None, cabinet: str | None = CABINET_ORIGIN
) -> StripeBillingAdapter:
    clock = AdjustableClock()
    return StripeBillingAdapter(
        stripe_client=None if sandbox is None else build_stripe_client(sandbox=sandbox),
        cabinet_base_url=None if cabinet is None else CabinetBaseUrl(cabinet),
        wall_clock=clock.wall_clock,
    )


def retry_request(reference: str | None) -> PaymentRetryRequest:
    return PaymentRetryRequest(
        provider=PaymentProvider.STRIPE,
        retry_id=derive_payment_retry_id(InvoiceId(), PaymentRetryAttempt(1)),
        payment_order_id=PaymentOrderId(),
        attempt=PaymentRetryAttempt(1),
        amount=euros(17500),
        description=InvoiceDescription("Call and message handling service"),
        language=LanguageTag("en"),
        failed_charge_reference=(
            None if reference is None else PaymentProviderReference(reference)
        ),
    )


def test_an_unconfigured_adapter_refuses_pages_and_events() -> None:
    adapter = build_adapter(None)

    with pytest.raises(ExternalServiceError):
        adapter.create_checkout(checkout_request(30 * DAY_SECONDS))

    with pytest.raises(AccessDeniedError):
        adapter.read_notification(
            PaymentWebhookDelivery(
                body=PaymentWebhookBody("{}"),
                provider=PaymentProvider.STRIPE,
                signature=PaymentWebhookSignature("t=1,v1=0"),
            )
        )


def test_pages_return_to_the_cabinet_without_a_return_link() -> None:
    sandbox = StripeSandbox()

    build_adapter(sandbox).create_checkout(checkout_request(30 * DAY_SECONDS))

    assert sandbox.checkout_sessions[0]["success_url"] == f"{CABINET_ORIGIN}/"
    with pytest.raises(ExternalServiceError):
        build_adapter(sandbox, cabinet=None).create_checkout(
            checkout_request(30 * DAY_SECONDS)
        )


def test_a_retry_pays_the_stripe_invoice_once() -> None:
    sandbox = StripeSandbox()
    adapter = build_adapter(sandbox)
    request = retry_request("in_test_0007")

    result = adapter.retry_charge(request)

    assert result.status is PaymentStatus.APPROVED
    assert sandbox.paid_invoices == ["in_test_0007"]
    assert sandbox.idempotency_keys == [f"retry:{request.retry_id}"]
    with pytest.raises(ValidationFailedError):
        adapter.retry_charge(retry_request(None))

    sandbox.is_card_declined = True
    declined = adapter.retry_charge(request)
    assert declined.status is PaymentStatus.DECLINED
    assert str(declined.failure_reason) == "insufficient_funds"
