"""The Flitt payment gateway adapter: checkouts and payment notifications."""

import json

import httpx
import pytest

from app.adapters.payments.flitt_payment_gateway_adapter import (
    FLITT_WEBHOOK_PATH,
    FlittPaymentGatewayAdapter,
    read_money,
    read_reference,
    select_page_language,
)
from app.clients.flitt.flitt_protocol import build_parameter_signature
from app.gateways.http import billing_routes
from app.schemas.constants.payments import PaymentStatus
from app.schemas.dto.billing import Money
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    PaymentNotification,
    PaymentWebhookDelivery,
    RecurringCharge,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import (
    BillingIntervalMonths,
    MoneyAmountMinor,
)
from app.schemas.typings.billing.constrained_strings import (
    AutoDebitStartDate,
    PaymentReturnUrl,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.billing.strings import (
    InvoiceDescription,
    PaymentProviderReference,
    PaymentWebhookBody,
    PaymentWebhookContentType,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from tests.billing.billing_settings import (
    APP_BASE_URL,
    CHECKOUT_URL,
    FLITT_MERCHANT_ID,
    FLITT_SECRET_KEY,
)
from tests.billing.flitt_sandbox import FlittSandbox
from tests.billing.flitt_test_clients import build_client, build_client_with


def build_checkout_request(language: str = "ka") -> PaymentCheckoutRequest:
    return PaymentCheckoutRequest(
        payment_order_id=PaymentOrderId(),
        amount=Money(
            amount_minor=MoneyAmountMinor(96000),
            currency_code=CurrencyCode("GEL"),
        ),
        description=InvoiceDescription("Call and message handling service"),
        recurring_charge=RecurringCharge(
            amount=Money(
                amount_minor=MoneyAmountMinor(51700),
                currency_code=CurrencyCode("GEL"),
            ),
            interval_months=BillingIntervalMonths(1),
            start_date=AutoDebitStartDate("2026-11-15"),
        ),
        language=LanguageTag(language),
        return_url=PaymentReturnUrl("https://app.assistant.example/billing"),
    )


def test_adapter_builds_a_subscription_checkout() -> None:
    sandbox = FlittSandbox()
    adapter = FlittPaymentGatewayAdapter(
        flitt_client=build_client(sandbox),
        app_base_url=PublicBaseUrl(f"{APP_BASE_URL}/"),
    )
    request: PaymentCheckoutRequest = build_checkout_request()

    session = adapter.create_checkout(request)

    assert str(session.checkout_url) == CHECKOUT_URL
    assert session.payment_reference == PaymentProviderReference("802345671")
    assert sandbox.checkout_orders == [
        {
            "order_id": str(request.payment_order_id),
            "order_desc": "Call and message handling service",
            "amount": 96000,
            "currency": "GEL",
            "server_callback_url": f"{APP_BASE_URL}{FLITT_WEBHOOK_PATH}",
            "merchant_data": str(request.payment_order_id),
            "subscription": "Y",
            "subscription_callback_url": f"{APP_BASE_URL}{FLITT_WEBHOOK_PATH}",
            "recurring_data": {
                "every": 1,
                "period": "month",
                "amount": 51700,
                "start_time": "2026-11-15",
                "state": "y",
                "readonly": "y",
            },
            "lang": "ka",
            "response_url": "https://app.assistant.example/billing",
            "merchant_id": 1549901,
        }
    ]


def test_adapter_and_router_share_the_webhook_path() -> None:
    assert billing_routes.FLITT_WEBHOOK_PATH == FLITT_WEBHOOK_PATH


def test_payment_page_language_only_when_flitt_has_it() -> None:
    assert select_page_language(LanguageTag("ka")) == "ka"
    assert select_page_language(LanguageTag("ru-KZ")) == "ru"
    assert select_page_language(LanguageTag("zh-Hant")) == "zh"
    assert select_page_language(LanguageTag("he")) is None
    assert select_page_language(LanguageTag("ar")) is None


def test_adapter_refuses_to_work_unconfigured() -> None:
    unconfigured = FlittPaymentGatewayAdapter(flitt_client=None, app_base_url=None)
    without_base_url = FlittPaymentGatewayAdapter(
        flitt_client=build_client(),
        app_base_url=None,
    )
    delivery = PaymentWebhookDelivery(body=PaymentWebhookBody("{}"))

    with pytest.raises(ExternalServiceError):
        unconfigured.create_checkout(build_checkout_request())

    with pytest.raises(ExternalServiceError):
        without_base_url.create_checkout(build_checkout_request())

    with pytest.raises(ExternalServiceError):
        unconfigured.stop_recurring(PaymentProviderReference("o-1"))

    with pytest.raises(AccessDeniedError):
        unconfigured.read_notification(delivery)


def test_adapter_rejects_a_page_link_flitt_did_not_send() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": {"response_status": "success"}})

    adapter = FlittPaymentGatewayAdapter(
        flitt_client=build_client_with(httpx.MockTransport(respond)),
        app_base_url=PublicBaseUrl(APP_BASE_URL),
    )

    with pytest.raises(ExternalServiceError):
        adapter.create_checkout(build_checkout_request())


def deliver(
    adapter: FlittPaymentGatewayAdapter,
    parameters: dict[str, object],
) -> PaymentNotification:
    body: str = json.dumps(
        {
            **parameters,
            "signature": build_parameter_signature(FLITT_SECRET_KEY, parameters),
        }
    )
    return adapter.read_notification(
        PaymentWebhookDelivery(
            body=PaymentWebhookBody(body),
            content_type=PaymentWebhookContentType("application/json"),
        )
    )


def test_adapter_reads_a_declined_notification() -> None:
    adapter = FlittPaymentGatewayAdapter(
        flitt_client=build_client(),
        app_base_url=PublicBaseUrl(APP_BASE_URL),
    )

    notification = deliver(
        adapter,
        {
            "order_id": "payment_order_x",
            "parent_order_id": "payment_order_parent",
            "merchant_id": FLITT_MERCHANT_ID,
            "order_status": "DECLINED",
            "amount": 51700,
            "currency": "gel",
            "payment_id": 77,
            "response_description": "  Insufficient funds  ",
        },
    )

    assert notification.status is PaymentStatus.DECLINED
    assert notification.order_reference == "payment_order_x"
    assert notification.parent_order_reference == "payment_order_parent"
    assert notification.payment_reference == "77"
    assert notification.amount == Money(
        amount_minor=MoneyAmountMinor(51700),
        currency_code=CurrencyCode("GEL"),
    )
    assert notification.failure_reason == "Insufficient funds"


def test_adapter_rejects_notifications_without_order_or_known_status() -> None:
    adapter = FlittPaymentGatewayAdapter(
        flitt_client=build_client(),
        app_base_url=PublicBaseUrl(APP_BASE_URL),
    )

    with pytest.raises(ValidationFailedError):
        deliver(adapter, {"merchant_id": FLITT_MERCHANT_ID, "order_status": "approved"})

    with pytest.raises(ValidationFailedError):
        deliver(
            adapter,
            {"order_id": "o", "merchant_id": FLITT_MERCHANT_ID, "order_status": "lost"},
        )


def test_reading_references_and_money_tolerates_provider_formats() -> None:
    assert read_reference(" 42 ") == "42"
    assert read_reference(42) == "42"
    assert read_reference(True) is None
    assert read_reference("") is None
    assert read_reference({"id": 1}) is None
    assert read_money("1000", "EUR") == Money(
        amount_minor=MoneyAmountMinor(1000),
        currency_code=CurrencyCode("EUR"),
    )
    assert read_money("10.00", "EUR") is None
    assert read_money(1000, "EURO") is None
    assert read_money(True, "EUR") is None
    assert read_money(1000, None) is None
