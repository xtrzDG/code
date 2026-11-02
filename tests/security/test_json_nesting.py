"""A JSON body nested deeper than the limit is refused (422) before parsing."""

import time
from typing import Annotated

import pytest
from base_pydantic_schemas import ImmutableDTO
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.gateways.http.application import build_http_application
from app.gateways.http.json_nesting import (
    MAX_JSON_NESTING_DEPTH,
    json_nesting_depth,
    looks_like_json,
)
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    read_raw_request_body,
)
from app.schemas.typings.platform.strings import ErrorMessageText


class NoteBody(ImmutableDTO):
    note: ErrorMessageText


class SilentErrorReporter:
    def capture_exception(self, error: BaseException) -> None:
        raise AssertionError(error)


def build_client() -> TestClient:
    router = APIRouter()
    read_note = build_json_body_dependency(NoteBody)

    @router.post("/v1/notes")
    def save(body: Annotated[NoteBody, Depends(read_note)]) -> dict[str, str]:
        return {"note": str(body.note)}

    @router.post("/v1/channels/meta/webhook")
    def raw(body: Annotated[bytes, Depends(read_raw_request_body)]) -> dict[str, int]:
        return {"length": len(body)}

    application = build_http_application(
        routers=[router], error_reporter=SilentErrorReporter(), cors_allowed_origins=[]
    )
    return TestClient(application)


def nested(depth: int) -> bytes:
    return b'{"note": "x", "deep": ' + b"[" * depth + b"]" * depth + b"}"


@pytest.mark.parametrize(
    ("body", "depth"),
    [
        (b"{}", 1),
        (b'{"a": [1, {"b": []}]}', 4),
        (b'{"a": "[[[[[[ text, not nesting ]]]"}', 1),
        (b'{"a": "a \\" [[[[ still text"}', 1),
        (b"not json", 0),
        (b"]]]][[", 2),
    ],
)
def test_the_depth_ignores_brackets_inside_strings(body: bytes, depth: int) -> None:
    assert json_nesting_depth(body) == depth


def test_a_body_at_the_limit_is_parsed_and_one_deeper_is_refused() -> None:
    client = build_client()

    # The object around the arrays is one level too.
    within = client.post("/v1/notes", content=nested(MAX_JSON_NESTING_DEPTH - 1))
    deeper = client.post("/v1/notes", content=nested(MAX_JSON_NESTING_DEPTH))
    hostile = client.post("/v1/notes", content=nested(100_000))

    assert within.status_code == 422  # parsed: "deep" is not a field
    assert "too_deep" not in within.text
    for refused in (deeper, hostile):
        assert refused.status_code == 422
        assert refused.json()["reasons"][0]["code"] == "too_deep"


def test_a_raw_json_webhook_body_is_measured_too() -> None:
    client = build_client()
    signed = {"X-Hub-Signature-256": "sha256=" + "0" * 64}

    refused = client.post(
        "/v1/channels/meta/webhook", content=nested(5_000), headers=signed
    )
    form = client.post(
        "/v1/channels/meta/webhook",
        content=b"a=" + b"[" * 5_000,
        headers={**signed, "Content-Type": "application/x-www-form-urlencoded"},
    )

    assert refused.status_code == 422
    assert refused.json()["reasons"][0]["code"] == "too_deep"
    assert form.status_code == 200


def test_what_counts_as_json() -> None:
    assert looks_like_json(b"x", "application/json; charset=utf-8")
    assert looks_like_json(b"  [1]", None)
    assert not looks_like_json(b"a=1", "application/x-www-form-urlencoded")
    assert not looks_like_json(b"", None)


def test_measuring_a_large_body_is_fast() -> None:
    body: bytes = b'{"items": [' + b'{"text": "a [b] {c}", "n": 1},' * 50_000 + b"1]}"

    started = time.perf_counter()
    depth = json_nesting_depth(body)

    assert depth == 3
    assert time.perf_counter() - started < 1.0
