import base64
import hashlib
import json
from urllib.parse import urlencode

import httpx
import pytest

from app.adapters.payments.flitt_payment_gateway_adapter import (
    FLITT_WEBHOOK_PATH,
    FlittPaymentGatewayAdapter,
    read_money,
    read_reference,
    select_page_language,
)
from app.clients.flitt.flitt_client import FlittClient
from app.clients.flitt.flitt_protocol import (
    build_envelope_signature,
    build_parameter_signature,
    decode_envelope_data,
    encode_envelope_data,
    is_signature_valid,
    parse_callback_parameters,
)
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
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from tests.billing.billing_testbed import (
    APP_BASE_URL,
    CHECKOUT_URL,
    FLITT_MERCHANT_ID,
    FLITT_SECRET_KEY,
    FlittSandbox,
)


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def build_client(handler: FlittSandbox | None = None) -> FlittClient:
    sandbox: FlittSandbox = handler or FlittSandbox()
    return FlittClient(
        merchant_id=PlatformIdentifier(FLITT_MERCHANT_ID),
        secret_key=PlatformSecret(FLITT_SECRET_KEY),
        transport=httpx.MockTransport(sandbox.handle),
    )


def build_client_with(handler: httpx.MockTransport) -> FlittClient:
    return FlittClient(
        merchant_id=PlatformIdentifier(FLITT_MERCHANT_ID),
        secret_key=PlatformSecret(FLITT_SECRET_KEY),
        api_base_url=PublicBaseUrl("https://pay.flitt.example"),
        transport=handler,
    )


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


def test_parameter_signature_matches_the_flitt_documentation_example() -> None:
    parameters: dict[str, object] = {
        "order_id": "TestOrder2",
        "order_desc": "Test payment",
        "currency": "GEL",
        "amount": 1000,
        "merchant_id": 1549901,
        "server_callback_url": "http://myshop/callback/",
    }

    assert build_parameter_signature("test", parameters) == sha1(
        "test|1000|GEL|1549901|Test payment|TestOrder2|http://myshop/callback/"
    )


def test_signature_skips_empty_values_and_its_own_fields() -> None:
    parameters: dict[str, object] = {
        "b": "two",
        "a": "one",
        "empty": "",
        "missing": None,
        "signature": "abc",
        "response_signature_string": "secret|...",
    }

    assert build_parameter_signature("key", parameters) == sha1("key|one|two")


def test_signature_values_follow_the_flitt_module_rules() -> None:
    parameters: dict[str, object] = {
        "a_true": True,
        "b_false": False,
        "c_whole_float": 10.0,
        "d_float": 10.5,
        "e_text": "გამარჯობა",
    }

    assert build_parameter_signature("key", parameters) == sha1(
        "key|1||10|10.5|გამარჯობა"
    )


def test_nested_values_cannot_be_signed() -> None:
    with pytest.raises(ValidationFailedError):
        build_parameter_signature("key", {"recurring_data": {"every": 1}})


def test_envelope_round_trip_and_signature() -> None:
    order: dict[str, object] = {"order_id": "o-1", "amount": 51700, "lang": "ka"}
    data: str = encode_envelope_data(order)

    assert json.loads(base64.b64decode(data)) == {"order": order}
    assert decode_envelope_data(data) == order
    assert build_envelope_signature("test", data) == sha1(f"test|{data}")


def test_envelope_without_order_object_returns_the_object_itself() -> None:
    data: str = base64.b64encode(b'{"response_status": "success"}').decode()

    assert decode_envelope_data(data) == {"response_status": "success"}


@pytest.mark.parametrize(
    "data",
    [
        "not base64!",
        base64.b64encode(b"[1, 2]").decode(),
        base64.b64encode(b"{").decode(),
    ],
)
def test_malformed_envelope_data_is_rejected(data: str) -> None:
    with pytest.raises(ValidationFailedError):
        decode_envelope_data(data)


def test_signature_comparison_ignores_case_and_rejects_other_types() -> None:
    expected: str = sha1("x")

    assert is_signature_valid(expected, expected.upper())
    assert not is_signature_valid(expected, "")
    assert not is_signature_valid(expected, 12345)
    assert not is_signature_valid(expected, "ünïcode")


def test_callback_parameters_are_read_from_json_form_and_wrapped_bodies() -> None:
    assert parse_callback_parameters('{"order_id": "o1"}', None) == {"order_id": "o1"}
    assert parse_callback_parameters(
        '{"response": {"order_id": "o1"}}',
        "application/json",
    ) == {"order_id": "o1"}
    assert parse_callback_parameters(
        urlencode({"order_id": "o1", "rectoken": ""}),
        "application/x-www-form-urlencoded; charset=utf-8",
    ) == {"order_id": "o1", "rectoken": ""}


@pytest.mark.parametrize(
    "body",
    ["", "   ", "not json", "[1, 2]", '{"1": 2, "x": {"y": [1]}}' + " " * 70000],
)
def test_bad_callback_bodies_are_rejected(body: str) -> None:
    with pytest.raises(ValidationFailedError):
        parse_callback_parameters(body, "application/json")


def test_client_sends_a_signed_protocol_two_envelope() -> None:
    sandbox = FlittSandbox()
    client = build_client(sandbox)

    response = client.create_checkout_url({"order_id": "o-1", "amount": 100})

    assert response["checkout_url"] == CHECKOUT_URL
    assert sandbox.checkout_orders == [
        {"order_id": "o-1", "amount": 100, "merchant_id": 1549901}
    ]


def test_client_reads_signed_protocol_two_responses() -> None:
    inner: str = encode_envelope_data(
        {"response_status": "success", "checkout_url": CHECKOUT_URL}
    )

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "pay.flitt.example"
        return httpx.Response(
            200,
            json={
                "response": {
                    "version": "2.0",
                    "data": inner,
                    "signature": build_envelope_signature(FLITT_SECRET_KEY, inner),
                }
            },
        )

    client = build_client_with(httpx.MockTransport(respond))

    assert client.create_checkout_url({"order_id": "o-2"})["checkout_url"] == (
        CHECKOUT_URL
    )


def test_client_rejects_a_forged_response_signature() -> None:
    inner: str = encode_envelope_data({"response_status": "success"})

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"response": {"data": inner, "signature": "0" * 40}},
        )

    with pytest.raises(ExternalServiceError):
        build_client_with(httpx.MockTransport(respond)).create_checkout_url({})


def test_client_reports_refusals_without_request_data() -> None:
    sandbox = FlittSandbox(
        refusal={
            "response_status": "failure",
            "error_message": "Invalid currency",
            "error_code": 1013,
            "request_id": "r-77",
        }
    )

    with pytest.raises(ExternalServiceError) as raised:
        build_client(sandbox).create_checkout_url({"order_id": "o-3"})

    assert str(raised.value) == (
        "Flitt refused the request: Invalid currency, code 1013, request r-77."
    )


def test_client_turns_transport_and_http_errors_into_service_errors() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    def garbage(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>")

    with pytest.raises(ExternalServiceError):
        build_client_with(httpx.MockTransport(fail)).create_checkout_url({})

    with pytest.raises(ExternalServiceError):
        build_client_with(httpx.MockTransport(garbage)).create_checkout_url({})

    with pytest.raises(ExternalServiceError):
        build_client(FlittSandbox(http_status=503)).create_checkout_url({})


def test_client_stops_a_subscription() -> None:
    sandbox = FlittSandbox()

    build_client(sandbox).stop_subscription("payment_order_1")

    assert sandbox.stopped_orders == ["payment_order_1"]


def test_callbacks_are_verified_in_every_encoding() -> None:
    client = build_client()
    parameters: dict[str, object] = {
        "order_id": "o-1",
        "merchant_id": FLITT_MERCHANT_ID,
        "order_status": "approved",
        "amount": "51700",
        "currency": "GEL",
    }
    signature: str = build_parameter_signature(FLITT_SECRET_KEY, parameters)
    flat_json: str = json.dumps({**parameters, "signature": signature.upper()})
    form: str = urlencode({**parameters, "signature": signature})
    data: str = encode_envelope_data(parameters)
    envelope: str = json.dumps(
        {
            "version": "2.0",
            "data": data,
            "signature": build_envelope_signature(FLITT_SECRET_KEY, data),
        }
    )

    assert client.verify_callback(flat_json, "application/json")["order_id"] == "o-1"
    assert (
        client.verify_callback(form, "application/x-www-form-urlencoded")["amount"]
        == "51700"
    )
    assert client.verify_callback(envelope, None)["order_status"] == "approved"


def test_callbacks_with_wrong_signature_or_merchant_are_refused() -> None:
    client = build_client()
    parameters: dict[str, object] = {
        "order_id": "o-1",
        "merchant_id": "999",
        "order_status": "approved",
    }
    wrong_merchant: str = json.dumps(
        {
            **parameters,
            "signature": build_parameter_signature(FLITT_SECRET_KEY, parameters),
        }
    )
    tampered: str = json.dumps(
        {
            **parameters,
            "merchant_id": FLITT_MERCHANT_ID,
            "signature": build_parameter_signature(FLITT_SECRET_KEY, parameters),
        }
    )
    data: str = encode_envelope_data(parameters)
    forged_envelope: str = json.dumps(
        {"version": "2.0", "data": data, "signature": sha1(f"other|{data}")}
    )

    for body in (wrong_merchant, tampered, forged_envelope):
        with pytest.raises(AccessDeniedError):
            client.verify_callback(body, "application/json")


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
