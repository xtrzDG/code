"""
Stripe's wire protocol: form-encoded nested parameters, webhook signatures
(`Stripe-Signature`: a timestamp and HMAC-SHA256 signatures of
"{timestamp}.{payload}" with the endpoint's signing secret) and its error
bodies. https://docs.stripe.com/api and https://docs.stripe.com/webhooks.
"""

import hashlib
import hmac
import json
from collections.abc import Mapping, Sequence
from typing import cast

from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ValidationFailedError,
)

SIGNATURE_SCHEME: str = "v1"
TIMESTAMP_KEY: str = "t"
# A notification older (or newer) than this is refused: a replayed one.
SIGNATURE_TOLERANCE_SECONDS: int = 300
MAX_REPORTED_ERROR_LENGTH: int = 120

type FormValue = str | int | bool | Mapping[str, "FormValue"] | Sequence["FormValue"]


def encode_form(parameters: Mapping[str, FormValue]) -> list[tuple[str, str]]:
    """
    Stripe's form encoding of nested parameters:
    {"line_items": [{"quantity": 1}]} -> [("line_items[0][quantity]", "1")].
    """

    pairs: list[tuple[str, str]] = []
    for name, value in parameters.items():
        pairs.extend(_encode_value(name, value))

    return pairs


def _encode_value(prefix: str, value: FormValue) -> list[tuple[str, str]]:
    if isinstance(value, bool):
        return [(prefix, "true" if value else "false")]

    if isinstance(value, int | str):
        return [(prefix, str(value))]

    if isinstance(value, Mapping):
        return [
            pair
            for key, item in value.items()
            for pair in _encode_value(f"{prefix}[{key}]", item)
        ]

    return [
        pair
        for index, item in enumerate(value)
        for pair in _encode_value(f"{prefix}[{index}]", item)
    ]


def verify_signature(
    payload: str,
    signature_header: str,
    signing_secret: str,
    now_unix_seconds: int,
) -> None:
    """
    Raises:
        AccessDeniedError: no valid v1 signature of this payload, or its
            timestamp is outside the tolerance (a replay).
    """

    timestamp: int | None = None
    signatures: list[str] = []
    for item in signature_header.split(","):
        key, separator, value = item.strip().partition("=")
        if separator != "=":
            continue

        if key == TIMESTAMP_KEY and value.isdigit():
            timestamp = int(value)
        elif key == SIGNATURE_SCHEME:
            signatures.append(value)

    if timestamp is None or not signatures:
        raise AccessDeniedError("Payment notification signature is invalid.")

    expected: str = hmac.new(
        signing_secret.encode("utf-8"),
        f"{timestamp}.{payload}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not any(hmac.compare_digest(expected, received) for received in signatures):
        raise AccessDeniedError("Payment notification signature is invalid.")

    if abs(now_unix_seconds - timestamp) > SIGNATURE_TOLERANCE_SECONDS:
        raise AccessDeniedError("Payment notification is too old.")


def parse_event(payload: str) -> dict[str, object]:
    """
    Raises:
        ValidationFailedError: not a JSON object with a type and an object.
    """

    try:
        event: object = json.loads(payload)
    except ValueError as error:
        raise ValidationFailedError(
            "Payment notification is not valid JSON."
        ) from error

    if not isinstance(event, dict):
        raise ValidationFailedError("Payment notification is not an object.")

    parsed: dict[str, object] = cast(dict[str, object], event)
    data: object = parsed.get("data")
    if (
        not isinstance(parsed.get("type"), str)
        or not isinstance(data, dict)
        or not isinstance(cast(dict[str, object], data).get("object"), dict)
    ):
        raise ValidationFailedError("Payment notification has no event object.")

    return parsed


def read_error(body: object) -> tuple[str, str]:
    """Stripe's error type and code (its message is never reported)."""

    if not isinstance(body, dict):
        return "unknown", "unknown"

    error: object = cast(dict[str, object], body).get("error")
    if not isinstance(error, dict):
        return "unknown", "unknown"

    fields: dict[str, object] = cast(dict[str, object], error)
    code: object = fields.get("decline_code") or fields.get("code")
    return (
        str(fields.get("type", "unknown"))[:MAX_REPORTED_ERROR_LENGTH],
        str(code or "unknown")[:MAX_REPORTED_ERROR_LENGTH],
    )
