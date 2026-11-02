"""
Every documented API operation answers malformed, hostile and random
requests with a 4xx, never a 5xx: path ids of any shape, odd query values
and random JSON bodies (with the operation's own field names), sent by a
signed-in owner (also for the business it owns). Deterministic (derandomized,
no example database) and a few examples per operation, so it stays fast.
"""

import json

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
from tests.e2e.harness import start_workshop

OPERATIONS: list[Operation] = documented_operations(
    start_workshop().application.openapi()
)
EXAMPLES_PER_OPERATION: int = 3

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

    assert response.status_code < 500, (
        f"{operation.label} -> {response.status_code}: {response.text[:300]}"
    )
