"""
The API definition ZAP's /v1 baseline imports (scripts/zap_api_definition.py):
read-only, no endless streams, the seeded business in its paths.
"""

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

import pytest

from scripts.zap_api_definition import main, read_only_definition
from tests.platform.environment_sources import ROOT

OPENAPI: Path = ROOT / "web" / "openapi.json"
BUSINESS_ID: str = "business_0000-test"
BUSINESS_PARAMETER: dict[str, Any] = {
    "name": "business_id",
    "in": "path",
    "required": True,
    "schema": {"type": "string"},
}
LIMIT_PARAMETER: dict[str, Any] = {
    "name": "limit",
    "in": "query",
    "schema": {"type": "integer"},
}


def operation(
    *parameters: dict[str, Any], media_type: str = "application/json"
) -> dict[str, Any]:
    return {
        "parameters": list(parameters),
        "responses": {"200": {"description": "ok", "content": {media_type: {}}}},
    }


SPEC: dict[str, Any] = {
    "openapi": "3.1.0",
    "info": {"title": "Assistant Workshop API", "version": "1"},
    "servers": [{"url": "https://api.example.com"}],
    "components": {"schemas": {"Problem": {"type": "object"}}},
    "paths": {
        "/healthz": {"get": operation()},
        "/v1/businesses/{business_id}/bookings": {
            "get": operation(BUSINESS_PARAMETER, LIMIT_PARAMETER),
            "post": operation(BUSINESS_PARAMETER),
        },
        "/v1/businesses/{business_id}/events": {
            "get": operation(BUSINESS_PARAMETER, media_type="text/event-stream"),
        },
        "/v1/businesses/{business_id}": {"delete": operation(BUSINESS_PARAMETER)},
    },
}


def test_only_reads_are_kept_with_the_seeded_business() -> None:
    result = read_only_definition(SPEC, "http://localhost:8000", BUSINESS_ID)

    assert result["servers"] == [{"url": "http://localhost:8000"}]
    assert result["components"] == SPEC["components"]
    assert set(result["paths"]) == {
        "/healthz",
        f"/v1/businesses/{BUSINESS_ID}/bookings",
    }
    bookings = result["paths"][f"/v1/businesses/{BUSINESS_ID}/bookings"]
    assert set(bookings) == {"get"}
    assert bookings["get"]["parameters"] == [LIMIT_PARAMETER]
    # The committed definition itself is left as it was.
    assert (
        SPEC["paths"]["/v1/businesses/{business_id}/bookings"]["get"]["parameters"][0]
        == BUSINESS_PARAMETER
    )


def test_the_committed_definition_gives_a_read_only_scan_of_the_api() -> None:
    definition = json.loads(OPENAPI.read_text(encoding="utf-8"))

    result = read_only_definition(definition, "http://localhost:8000", BUSINESS_ID)
    serialized = json.dumps(result)

    assert len(result["paths"]) > 100
    assert all(set(item) <= {"get", "parameters"} for item in result["paths"].values())
    assert "{business_id}" not in serialized
    assert "text/event-stream" not in json.dumps(result["paths"])
    assert any(
        path.startswith(f"/v1/businesses/{BUSINESS_ID}/") for path in result["paths"]
    )


def run(*arguments: str) -> tuple[int, str, str]:
    output, errors = io.StringIO(), io.StringIO()
    with redirect_stdout(output), redirect_stderr(errors):
        code = main(list(arguments))
    return code, output.getvalue(), errors.getvalue()


def test_the_command_writes_the_definition(tmp_path: Path) -> None:
    source = tmp_path / "openapi.json"
    source.write_text(json.dumps(SPEC), encoding="utf-8")

    code, output, _ = run(
        str(source), "--server", "http://localhost:8000/", "--business-id", BUSINESS_ID
    )

    assert code == 0
    assert json.loads(output)["servers"] == [{"url": "http://localhost:8000"}]


@pytest.mark.parametrize(
    ("server", "business_id", "message"),
    [
        ("localhost:8000", BUSINESS_ID, "--server"),
        ("http://localhost:8000", "../../etc", "--business-id"),
        ("http://localhost:8000", "", "--business-id"),
    ],
)
def test_wrong_arguments_exit_2(
    tmp_path: Path, server: str, business_id: str, message: str
) -> None:
    source = tmp_path / "openapi.json"
    source.write_text(json.dumps(SPEC), encoding="utf-8")

    code, output, errors = run(
        str(source), "--server", server, "--business-id", business_id
    )

    assert code == 2
    assert output == ""
    assert message in errors


def test_an_unusable_definition_exits_2(tmp_path: Path) -> None:
    source = tmp_path / "openapi.json"
    source.write_text('{"openapi": "3.1.0"}', encoding="utf-8")

    code, output, errors = run(
        str(source), "--server", "http://x", "--business-id", BUSINESS_ID
    )

    assert (code, output) == (2, "")
    assert "not a usable OpenAPI definition" in errors
