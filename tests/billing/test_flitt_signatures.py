"""Flitt protocol 2.0 signatures, envelopes and callback bodies."""

import base64
import json
from urllib.parse import urlencode

import pytest

from app.clients.flitt.flitt_protocol import (
    build_envelope_signature,
    build_parameter_signature,
    decode_envelope_data,
    encode_envelope_data,
    is_signature_valid,
    parse_callback_parameters,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from tests.billing.flitt_test_clients import sha1


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
