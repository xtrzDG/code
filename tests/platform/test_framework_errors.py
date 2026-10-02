"""
The framework's own refusals speak the API's one error language: a missing
or malformed parameter, an unknown route or method are `ErrorBody` answers,
and the API description shows no FastAPI validation schemas.
"""

import asyncio
from typing import Annotated, Any

import pytest
from fastapi import APIRouter, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from app.gateways.http.error_responses import (
    describe_field_error,
    handle_http_exception,
    handle_request_validation_error,
    install_error_handlers,
)
from app.gateways.http.openapi_error_contract import (
    describe_errors_as_error_body,
    standard_error_responses,
)


def build_client() -> TestClient:
    return TestClient(build_application())


def build_application() -> FastAPI:
    http_application = FastAPI()
    install_error_handlers(http_application)
    router = APIRouter(responses=standard_error_responses(404, 422))

    @router.get("/plans")
    def plans(
        country_code: Annotated[str, Query()],
        limit: Annotated[int, Query()] = 10,
    ) -> dict[str, str]:
        return {"country": country_code, "limit": str(limit)}

    @router.get("/widget")
    def widget(session_key: Annotated[str, Header()]) -> dict[str, str]:
        return {"session": session_key}

    @router.get("/challenge", response_class=PlainTextResponse)
    def challenge(mode: Annotated[str, Query()]) -> str:
        return mode

    http_application.include_router(router)
    return http_application


def test_a_missing_query_parameter_is_an_error_body_with_a_reason() -> None:
    response = build_client().get("/plans")

    assert response.status_code == 422
    assert response.json() == {
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


def test_a_malformed_value_is_invalid_without_echoing_it() -> None:
    response = build_client().get(
        "/plans", params={"country_code": "GE", "limit": "secret-text"}
    )

    body: dict[str, Any] = response.json()
    assert response.status_code == 422
    assert [reason["code"] for reason in body["reasons"]] == ["invalid"]
    assert body["reasons"][0]["details"] == ["query.limit"]
    assert "secret-text" not in response.text


def test_a_missing_header_is_reported_by_its_location() -> None:
    response = build_client().get("/widget")

    assert response.status_code == 422
    assert response.json()["reasons"][0]["details"] == ["header.session-key"]


def test_unknown_routes_and_methods_keep_their_status() -> None:
    client = build_client()

    unknown = client.get("/nowhere")
    wrong_method = client.post("/plans")

    assert unknown.status_code == 404
    assert unknown.json() == {"error": "not_found", "message": "Not Found"}
    assert wrong_method.status_code == 405
    assert wrong_method.json() == {
        "error": "validation_failed",
        "message": "Method Not Allowed",
    }
    assert wrong_method.headers["Allow"] == "GET"


def test_a_location_that_is_not_a_safe_token_is_left_out() -> None:
    reason = describe_field_error(
        {"type": "value_error", "loc": ("body", "a field"), "msg": "Bad."}
    )
    nowhere = describe_field_error({"type": "missing", "msg": "Field required"})

    assert (str(reason.code), reason.details) == ("invalid", [])
    assert (str(nowhere.code), [str(item) for item in nowhere.details]) == (
        "missing",
        ["request"],
    )


def test_handlers_answer_other_exceptions_without_details() -> None:
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})

    validation = asyncio.run(handle_request_validation_error(request, ValueError()))
    empty = asyncio.run(
        handle_request_validation_error(request, RequestValidationError([]))
    )
    other = asyncio.run(handle_http_exception(request, ValueError("x")))

    assert (validation.status_code, empty.status_code) == (422, 422)
    assert bytes(validation.body) == (
        b'{"error":"validation_failed","message":"Invalid request."}'
    )
    assert other.status_code == 500
    assert b'"internal_error"' in bytes(other.body)


def test_the_description_names_only_error_body_for_errors() -> None:
    document: dict[str, Any] = build_application().openapi()

    schemas: dict[str, Any] = document["components"]["schemas"]
    challenge = document["paths"]["/challenge"]["get"]["responses"]
    assert "HTTPValidationError" not in schemas
    assert "ValidationError" not in schemas
    assert set(challenge) == {"200", "404", "422"}
    assert challenge["422"]["content"] == {
        "application/json": {"schema": {"$ref": "#/components/schemas/ErrorBody"}}
    }


def test_framework_validation_responses_are_replaced_with_error_body() -> None:
    framework_reference = {"$ref": "#/components/schemas/HTTPValidationError"}
    document: dict[str, Any] = {
        "paths": {
            "/x": {
                "parameters": [],
                "get": {
                    "responses": {
                        "422": {
                            "content": {
                                "application/json": {"schema": framework_reference}
                            }
                        }
                    }
                },
            }
        },
        "components": {"schemas": {"HTTPValidationError": {}, "ValidationError": {}}},
    }

    described = describe_errors_as_error_body(document)

    schemas: dict[str, Any] = described["components"]["schemas"]
    assert set(schemas) == {"ErrorBody", "ErrorReason", "ApiErrorCode"}
    assert described["paths"]["/x"]["get"]["responses"]["422"]["content"] == {
        "application/json": {"schema": {"$ref": "#/components/schemas/ErrorBody"}}
    }


def test_standard_error_responses_default_to_the_cabinet_set() -> None:
    assert list(standard_error_responses()) == [401, 403, 404, 409, 422, 429, 502]
    assert list(standard_error_responses(404)) == [404]
    with pytest.raises(ValueError, match="418"):
        standard_error_responses(418)
