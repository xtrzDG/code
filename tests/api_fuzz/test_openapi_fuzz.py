"""
Every documented API operation answers malformed, hostile and random
requests with a 4xx, never a server error: path ids of any shape, odd
query values and random JSON bodies (with the operation's own field
names), sent by a signed-in owner (also for the business it owns). The one
5xx allowed is the documented 502 `external_service_error` of a provider
this test application has no account for (Google Calendar). The
operations come from the committed description (web/openapi.json, which
`npm run gen:api` keeps in step with the code). Deterministic
(derandomized, no example database), a few examples per operation.
"""

import json
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.api_fuzz.conftest import FUZZ_MARK, FuzzTarget
from tests.api_fuzz.fuzz_strategies import (
    FuzzRequest,
    Operation,
    documented_operations,
    requests_to,
)

DESCRIPTION: Path = Path(__file__).resolve().parents[2] / "web" / "openapi.json"
OPERATIONS: list[Operation] = documented_operations(
    json.loads(DESCRIPTION.read_text(encoding="utf-8"))
)
EXAMPLES_PER_OPERATION: int = 3
PROVIDER_UNAVAILABLE: tuple[int, str] = (502, "external_service_error")

pytestmark = pytest.mark.api_fuzz


def test_the_fuzz_mark_is_the_registered_one() -> None:
    assert pytestmark.name == FUZZ_MARK
    assert len(OPERATIONS) > 300


@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda op: op.label)
@settings(
    max_examples=EXAMPLES_PER_OPERATION,
    derandomize=True,
    database=None,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
@given(data=st.data())
def test_no_operation_answers_a_server_error(
    fuzz_target: FuzzTarget, operation: Operation, data: st.DataObject
) -> None:
    fuzz_target.keep_signed_in()
    request: FuzzRequest = data.draw(requests_to(operation, fuzz_target.business_id))
    content: bytes | None = (
        None if operation.body_fields is None else json.dumps(request.body).encode()
    )

    response = fuzz_target.workshop.client.request(
        operation.method.upper(),
        request.path,
        params=request.params,
        content=content,
        headers={**fuzz_target.headers(), "Content-Type": "application/json"},
    )

    outcome: tuple[int, str] = (
        response.status_code,
        str(response.json().get("error")) if response.status_code >= 500 else "",
    )
    assert response.status_code < 500 or outcome == PROVIDER_UNAVAILABLE, (
        f"{operation.label} -> {response.status_code}: {response.text[:300]}"
    )
