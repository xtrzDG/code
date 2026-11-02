"""
Every documented operation with a JSON body answers hostile bodies with a
4xx, never a server error, also when the request carries an
Idempotency-Key (its fingerprint reads the body before the route does):
a body nested far deeper than the limit, a lone surrogate (valid JSON, no
UTF-8) and a string of escaped quotes (once quadratic to measure).
"""

import json
from pathlib import Path
from uuid import uuid4

import pytest

from tests.api_fuzz.conftest import FuzzTarget
from tests.api_fuzz.fuzz_strategies import Operation, documented_operations

DESCRIPTION: Path = Path(__file__).resolve().parents[2] / "web" / "openapi.json"
BODY_OPERATIONS: list[Operation] = [
    operation
    for operation in documented_operations(
        json.loads(DESCRIPTION.read_text(encoding="utf-8"))
    )
    if operation.body_fields is not None
]
HOSTILE_BODIES: dict[str, bytes] = {
    "deep": b"[" * 100_000 + b"]" * 100_000,
    "lone-surrogate": b'{"name": "\\ud800", "text": "\\udfff"}',
    "escaped-quotes": b'{"text": "' + b'\\"' * 60_000 + b'"}',
}
PROVIDER_UNAVAILABLE: tuple[int, str] = (502, "external_service_error")

pytestmark = pytest.mark.api_fuzz


def path_of(operation: Operation, business_id: str) -> str:
    path: str = operation.path
    for name in operation.path_parameters:
        value: str = business_id if name == "business_id" else f"{name}_0"
        path = path.replace("{" + name + "}", value)

    return path


def test_the_sweep_covers_the_body_operations() -> None:
    assert len(BODY_OPERATIONS) > 100


@pytest.mark.parametrize("body_name", sorted(HOSTILE_BODIES))
@pytest.mark.parametrize("operation", BODY_OPERATIONS, ids=lambda op: op.label)
def test_no_operation_answers_a_hostile_body_with_a_server_error(
    fuzz_target: FuzzTarget, operation: Operation, body_name: str
) -> None:
    fuzz_target.keep_signed_in()

    response = fuzz_target.workshop.client.request(
        operation.method.upper(),
        path_of(operation, fuzz_target.business_id),
        content=HOSTILE_BODIES[body_name],
        headers={
            **fuzz_target.headers(),
            "Content-Type": "application/json",
            "Idempotency-Key": str(uuid4()),
        },
    )

    outcome: tuple[int, str] = (
        response.status_code,
        str(response.json().get("error")) if response.status_code >= 500 else "",
    )
    assert response.status_code < 500 or outcome == PROVIDER_UNAVAILABLE, (
        f"{operation.label} ({body_name}) -> {response.status_code}: "
        f"{response.text[:300]}"
    )
