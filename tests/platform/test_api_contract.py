"""
The API speaks one error language (docs/api-versioning.md): every error an
operation documents is an `ErrorBody`, FastAPI's own validation schemas are
gone from the description, every DELETE answers 204 No Content, and paged
lists answer `{"items": [...], "next_cursor": ...}`. At runtime the
framework's refusals (a missing query parameter or header, an unknown route
or method) are `ErrorBody` answers too. Every operation has a tag and a
readable operationId, `<tag>_<route function name>` in snake_case, unique
across the description (what an SDK generator turns into method names).
"""

import re
from collections.abc import Iterator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from tests.e2e.harness import start_workshop

type JsonObject = dict[str, Any]

ERROR_BODY_REFERENCE: str = "#/components/schemas/ErrorBody"
STANDARD_ERROR_STATUSES: set[str] = {"401", "403", "404", "409", "422", "429", "502"}
HTTP_METHODS: tuple[str, ...] = ("get", "post", "put", "patch", "delete")
SNAKE_CASE_ID: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")


@pytest.fixture(scope="module")
def description() -> JsonObject:
    return start_workshop().application.openapi()


def operations(description: JsonObject) -> Iterator[tuple[str, JsonObject]]:
    for path, path_item in cast(dict[str, JsonObject], description["paths"]).items():
        for method in HTTP_METHODS:
            if method in path_item:
                yield f"{method.upper()} {path}", cast(JsonObject, path_item[method])


def schema_of(response: JsonObject) -> JsonObject:
    content = cast(dict[str, JsonObject], response.get("content", {}))
    return cast(JsonObject, content.get("application/json", {}).get("schema", {}))


def test_every_documented_error_is_an_error_body(description: JsonObject) -> None:
    wrong: list[str] = []
    for key, operation in operations(description):
        responses = cast(dict[str, JsonObject], operation["responses"])
        for status_code, response in responses.items():
            is_error = int(status_code) >= 400
            content = cast(dict[str, object], response.get("content", {}))
            if is_error and (
                list(content) != ["application/json"]
                or schema_of(response).get("$ref") != ERROR_BODY_REFERENCE
            ):
                wrong.append(f"{key} {status_code}: {content}")

    assert wrong == []


def test_every_operation_documents_the_standard_errors(
    description: JsonObject,
) -> None:
    missing: dict[str, list[str]] = {
        key: sorted(STANDARD_ERROR_STATUSES - set(operation["responses"]))
        for key, operation in operations(description)
        if not set(operation["responses"]) >= STANDARD_ERROR_STATUSES
    }

    assert missing == {}


def test_framework_validation_schemas_are_gone(description: JsonObject) -> None:
    schemas = cast(JsonObject, description["components"]["schemas"])
    text: str = str(description)

    assert "HTTPValidationError" not in schemas
    assert "ValidationError" not in schemas
    assert "HTTPValidationError" not in text
    assert set(schemas["ErrorBody"]["properties"]) == {"error", "message", "reasons"}
    assert "internal_error" in schemas["ApiErrorCode"]["enum"]


def test_every_delete_answers_no_content(description: JsonObject) -> None:
    deletes: dict[str, list[str]] = {
        key: sorted(code for code in operation["responses"] if int(code) < 400)
        for key, operation in operations(description)
        if key.startswith("DELETE ")
    }

    assert len(deletes) >= 7
    assert {key: codes for key, codes in deletes.items() if codes != ["204"]} == {}
    assert all(
        "content" not in operation["responses"]["204"]
        for key, operation in operations(description)
        if key.startswith("DELETE ")
    )


def test_paged_lists_answer_items_and_next_cursor(description: JsonObject) -> None:
    schemas = cast(dict[str, JsonObject], description["components"]["schemas"])
    paged: dict[str, set[str]] = {}
    for key, operation in operations(description):
        parameters = cast(list[JsonObject], operation.get("parameters", []))
        if "cursor" not in {parameter["name"] for parameter in parameters}:
            continue

        reference = str(schema_of(operation["responses"]["200"])["$ref"])
        page = schemas[reference.rsplit("/", 1)[-1]]
        paged[key] = {"items", "next_cursor"} - set(page["properties"])
        assert page["properties"]["items"]["type"] == "array", key

    assert len(paged) >= 9
    assert {key: gaps for key, gaps in paged.items() if gaps} == {}


def test_operation_ids_are_unique_snake_case_tag_and_function_names(
    description: JsonObject,
) -> None:
    ids: dict[str, list[str]] = {}
    for key, operation in operations(description):
        ids.setdefault(str(operation["operationId"]), []).append(key)
    untagged: list[str] = [
        key for key, operation in operations(description) if not operation.get("tags")
    ]
    by_key: dict[str, JsonObject] = dict(operations(description))

    assert len(ids) >= 300
    assert {name: keys for name, keys in ids.items() if len(keys) > 1} == {}
    assert [name for name in ids if not SNAKE_CASE_ID.match(name)] == []
    assert [name for name in ids if name.endswith("_route")] == []
    assert untagged == []
    assert by_key["GET /v1/admin/clients"]["operationId"] == "admin_list_clients"
    assert (
        by_key["POST /v1/businesses/{business_id}/bookings"]["operationId"]
        == "operations_post_booking"
    )
    assert (
        by_key["GET /v1/admin/clients/{business_id}/quality"]["operationId"]
        == "quality_get_client_quality"
    )
    assert (
        by_key["GET /v1/catalog/countries"]["operationId"] == "catalog_list_countries"
    )


def test_framework_refusals_are_error_bodies_at_runtime() -> None:
    client: TestClient = start_workshop().client
    without_country = client.get("/v1/catalog/plans")
    without_session = client.get("/v1/widget/business_x/messages")
    unknown_route = client.get("/v1/nowhere")
    wrong_method = client.put("/v1/catalog/countries")

    assert without_country.status_code == 422
    assert without_country.json() == {
        "error": "validation_failed",
        "message": "Invalid request: query.country_code: Field required",
        "reasons": [
            {
                "code": "missing",
                "message": "Field required",
                "details": ["query.country_code"],
            }
        ],
    }
    assert without_session.status_code == 422
    assert without_session.json()["reasons"][0]["details"] == [
        "header.X-Widget-Session-Key"
    ]
    assert (unknown_route.status_code, unknown_route.json()["error"]) == (
        404,
        "not_found",
    )
    assert (wrong_method.status_code, wrong_method.json()["error"]) == (
        405,
        "validation_failed",
    )
