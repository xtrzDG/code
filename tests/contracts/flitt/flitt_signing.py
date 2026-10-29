"""
Flitt's documented signatures, written from the protocol pages rather
than taken from the client, so the client is checked against them.

Protocol 1.0: sha1 of the secret and the non-empty parameter values
sorted by name, joined with "|" (`signature` and
`response_signature_string` left out). Protocol 2.0: sha1 of
"<secret>|<base64 data>".
"""

import base64
import hashlib
import json
from typing import Any

UNSIGNED: frozenset[str] = frozenset({"signature", "response_signature_string"})
# The secret of Flitt's documented test merchant 1549901.
TEST_SECRET: str = "test"


def documented_signature(parameters: dict[str, Any], secret: str = TEST_SECRET) -> str:
    values: list[str] = [secret]
    for name in sorted(parameters):
        value: Any = parameters[name]
        if name in UNSIGNED or value is None or value == "":
            continue
        values.append(("1" if value else "") if isinstance(value, bool) else str(value))

    return hashlib.sha1("|".join(values).encode("utf-8")).hexdigest()


def signed(parameters: dict[str, Any]) -> dict[str, Any]:
    unsigned: dict[str, Any] = {
        name: value for name, value in parameters.items() if name not in UNSIGNED
    }
    return {**unsigned, "signature": documented_signature(unsigned)}


def envelope(order: dict[str, Any]) -> dict[str, Any]:
    """A protocol 2.0 callback carrying the order."""

    data: str = base64.b64encode(
        json.dumps({"order": order}, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    return {
        "version": "2.0",
        "data": data,
        "signature": hashlib.sha1(f"{TEST_SECRET}|{data}".encode()).hexdigest(),
    }


def opened(request_body: dict[str, Any]) -> dict[str, Any]:
    """The order inside a protocol 2.0 request, its signature checked."""

    request: dict[str, Any] = request_body["request"]
    data: str = request["data"]
    assert (
        request["signature"]
        == hashlib.sha1(f"{TEST_SECRET}|{data}".encode()).hexdigest()
    )
    order: dict[str, Any] = json.loads(base64.b64decode(data))["order"]
    return order
