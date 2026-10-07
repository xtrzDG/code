"""The Flitt client: signed requests and responses, refusals, callbacks."""

import json
from urllib.parse import urlencode

import httpx
import pytest

from app.clients.flitt.flitt_protocol import (
    build_envelope_signature,
    build_parameter_signature,
    encode_envelope_data,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
)
from tests.billing.billing_settings import (
    CHECKOUT_URL,
    FLITT_MERCHANT_ID,
    FLITT_SECRET_KEY,
)
from tests.billing.flitt_sandbox import FlittSandbox
from tests.billing.flitt_test_clients import build_client, build_client_with, sha1


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


def test_client_names_the_shape_of_a_refusal_without_a_message() -> None:
    sandbox = FlittSandbox(
        refusal={"response_status": "failure", "order_id": "o-4", "amount": 100}
    )

    with pytest.raises(ExternalServiceError) as raised:
        build_client(sandbox).create_checkout_url({"order_id": "o-4"})

    assert str(raised.value) == (
        "Flitt refused the request: no error message, status 'failure', "
        "fields amount, order_id, response_status."
    )
    assert "o-4" not in str(raised.value)


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
