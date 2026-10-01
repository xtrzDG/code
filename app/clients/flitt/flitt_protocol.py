"""
Signatures and envelopes of the Flitt payment API (Fondy-compatible).

Flat parameters (protocol 1.0, used by callbacks) are signed with
SHA-1 of "<secret>|" followed by the values of the non-empty parameters
sorted by name and joined with "|"; `signature` and
`response_signature_string` are left out. Example from the Flitt docs:
"test|1000|GEL|1549901|Test payment|TestOrder2|http://myshop/callback/".

Protocol 2.0 (needed for subscriptions, whose `recurring_data` is nested)
sends `{"version": "2.0", "data": <base64 JSON {"order": {...}}>,
"signature": sha1("<secret>|<data>")}`.

The value rules follow Flitt's own CS-Cart module: empty strings and nulls
are skipped, `true` is "1", `false` is an empty value that still counts.
Nested values cannot be signed this way and are rejected.
"""

import base64
import binascii
import hashlib
import hmac
import json
from collections.abc import Mapping
from typing import cast
from urllib.parse import parse_qsl

from app.schemas.exceptions.application_errors import ValidationFailedError

SIGNATURE_SEPARATOR: str = "|"
SIGNATURE_PARAMETER: str = "signature"
UNSIGNED_PARAMETERS: frozenset[str] = frozenset(
    {SIGNATURE_PARAMETER, "response_signature_string"}
)
ENVELOPE_VERSION: str = "2.0"
ENVELOPE_ORDER_KEY: str = "order"
RESPONSE_WRAPPER_KEY: str = "response"
FORM_CONTENT_TYPE: str = "application/x-www-form-urlencoded"
MAX_CALLBACK_BODY_LENGTH: int = 64 * 1024


def build_parameter_signature(secret_key: str, parameters: Mapping[str, object]) -> str:
    """Signature of flat parameters (protocol 1.0)."""

    signed_values: list[str] = [secret_key]
    for parameter_name in sorted(parameters):
        if parameter_name in UNSIGNED_PARAMETERS:
            continue

        signed_value: str | None = stringify_signature_value(
            parameter_name,
            parameters[parameter_name],
        )
        if signed_value is not None:
            signed_values.append(signed_value)

    return sha1_hex(SIGNATURE_SEPARATOR.join(signed_values))


def stringify_signature_value(parameter_name: str, value: object) -> str | None:
    """Text of one value in a signature, or None when the value is skipped."""

    if value is None:
        return None

    if isinstance(value, bool):
        return "1" if value else ""

    if isinstance(value, str):
        return None if value == "" else value

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)

    raise ValidationFailedError(
        f"Payment notification parameter {parameter_name!r} is not a plain value."
    )


def build_envelope_signature(secret_key: str, envelope_data: str) -> str:
    """Signature of a protocol 2.0 envelope: sha1("<secret>|<data>")."""

    return sha1_hex(f"{secret_key}{SIGNATURE_SEPARATOR}{envelope_data}")


def encode_envelope_data(order_parameters: Mapping[str, object]) -> str:
    """Base64 of the JSON object {"order": parameters}."""

    serialized: str = json.dumps(
        {ENVELOPE_ORDER_KEY: dict(order_parameters)},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return base64.b64encode(serialized.encode("utf-8")).decode("ascii")


def decode_envelope_data(envelope_data: str) -> dict[str, object]:
    """
    Parameters inside a protocol 2.0 envelope: the "order" object when
    present, otherwise the decoded object itself.

    Raises:
        ValidationFailedError: the data is not base64 JSON of an object.
    """

    try:
        decoded_text: str = base64.b64decode(envelope_data, validate=True).decode(
            "utf-8"
        )
        decoded: object = json.loads(decoded_text)
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise ValidationFailedError(
            "Payment envelope data is not base64-encoded JSON."
        ) from error

    mapping: dict[str, object] = require_mapping(decoded, "Payment envelope data")
    order: object = mapping.get(ENVELOPE_ORDER_KEY)
    if order is None:
        return mapping

    return require_mapping(order, "Payment envelope order")


def is_signature_valid(expected_signature: str, received_signature: object) -> bool:
    """Constant-time comparison; the received hex digest may be upper case."""

    if not isinstance(received_signature, str) or received_signature == "":
        return False

    return hmac.compare_digest(
        expected_signature.encode("ascii"),
        received_signature.strip().lower().encode("ascii", errors="replace"),
    )


def parse_callback_parameters(
    body: str,
    content_type: str | None,
) -> dict[str, object]:
    """
    Parameters of a callback sent as a JSON object or as an HTML form.

    A JSON body wrapped as {"response": {...}} is unwrapped.

    Raises:
        ValidationFailedError: the body is empty, too large or malformed.
    """

    if body.strip() == "":
        raise ValidationFailedError("Payment notification body is empty.")

    if len(body) > MAX_CALLBACK_BODY_LENGTH:
        raise ValidationFailedError("Payment notification body is too large.")

    if content_type is not None and content_type.lower().startswith(FORM_CONTENT_TYPE):
        return dict(parse_qsl(body, keep_blank_values=True))

    try:
        decoded: object = json.loads(body)
    except ValueError as error:
        raise ValidationFailedError(
            "Payment notification body is not JSON or form data."
        ) from error

    parameters: dict[str, object] = require_mapping(decoded, "Payment notification")
    wrapped: object = parameters.get(RESPONSE_WRAPPER_KEY)
    if len(parameters) == 1 and wrapped is not None:
        return require_mapping(wrapped, "Payment notification response")

    return parameters


def is_envelope(parameters: Mapping[str, object]) -> bool:
    """True for a protocol 2.0 envelope with base64 data."""

    return (
        str(parameters.get("version", "")) == ENVELOPE_VERSION
        and isinstance(parameters.get("data"), str)
        and SIGNATURE_PARAMETER in parameters
    )


def require_mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValidationFailedError(f"{label} must be a JSON object.")

    mapping: dict[object, object] = cast(dict[object, object], value)
    return {str(key): item for key, item in mapping.items()}


def sha1_hex(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()
