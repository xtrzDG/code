"""
A creating request with an Idempotency-Key and a hostile body is refused
like one without a key (422), never a server error: its fingerprint does
not parse a body nested deeper than the request limit (the parser would
recurse until it fails), and a lone surrogate, valid JSON but no UTF-8,
is fingerprinted as its own bytes.
"""

from app.gateways.http.idempotency.request_fingerprint import fingerprint_request
from app.gateways.http.json_nesting import MAX_JSON_NESTING_DEPTH
from tests.idempotency.idempotency_world import IdempotencyWorld
from tests.idempotency.idempotent_route_app import (
    THINGS,
    ThingMaker,
    build_thing_api,
    with_key,
)

KEY: str = "5b2c8e1f-3a4d-4e6f-8b9a-0c1d2e3f4a5b"
DEEP_BODY: bytes = b"[" * 100_000 + b"]" * 100_000
SURROGATE_BODY: bytes = b'{"name": "\\ud800"}'


def test_a_deep_body_with_a_key_is_refused_too_deep() -> None:
    maker = ThingMaker()
    client = build_thing_api(IdempotencyWorld(), maker)

    response = client.post(
        THINGS,
        content=DEEP_BODY,
        headers={**with_key(KEY), "Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["reasons"][0]["code"] == "too_deep"
    assert maker.runs == 0


def test_a_lone_surrogate_with_a_key_is_a_client_error() -> None:
    maker = ThingMaker()
    client = build_thing_api(IdempotencyWorld(), maker)

    response = client.post(
        THINGS,
        content=SURROGATE_BODY,
        headers={**with_key(KEY), "Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "validation_failed"
    assert maker.runs == 0


def test_hostile_bodies_have_a_fingerprint_of_their_own() -> None:
    at_limit: bytes = b"[" * MAX_JSON_NESTING_DEPTH + b"]" * MAX_JSON_NESTING_DEPTH
    fingerprints = {
        str(fingerprint_request("POST", THINGS, "", body))
        for body in (DEEP_BODY, SURROGATE_BODY, b'{"name": "\\ud801"}', at_limit)
    }

    assert len(fingerprints) == 4
    # Within the limit a body still counts by meaning (spacing ignored).
    assert fingerprint_request("POST", THINGS, "", at_limit) == fingerprint_request(
        "POST", THINGS, "", b" " + at_limit + b" "
    )
