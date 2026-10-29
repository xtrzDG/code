"""Cabinet CORS allow-list and the public widget routes."""

import pytest
from fastapi import APIRouter, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.gateways.http.application import build_http_application
from app.gateways.http.cabinet_cors_middleware import is_self_cors_path
from app.schemas.exceptions.application_errors import NotFoundError, RateLimitedError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds

WIDGET_HEADERS: dict[str, str] = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


class WidgetBody(BaseModel):
    text: str


class NoErrors:
    def capture_exception(self, error: BaseException) -> None:
        raise AssertionError(f"unexpected error {error!r}")


def build_client() -> TestClient:
    router = APIRouter()

    @router.options("/v1/widget/{business_id}/messages")
    def widget_preflight(business_id: str) -> Response:
        del business_id
        return Response(status_code=204, headers=WIDGET_HEADERS)

    @router.post("/v1/widget/{business_id}/messages")
    def widget_message(business_id: str) -> Response:
        return Response(content=business_id, headers=WIDGET_HEADERS)

    @router.get("/v1/me")
    def me() -> dict[str, str]:
        return {"user": "owner"}

    application = build_http_application(
        routers=[router],
        error_reporter=NoErrors(),
        cors_allowed_origins=[PublicBaseUrl("https://cabinet.example.com")],
    )
    return TestClient(application)


def test_widget_preflight_from_any_site_reaches_the_widget_route() -> None:
    client = build_client()

    preflight = client.options(
        "/v1/widget/biz_1/messages",
        headers={
            "Origin": "https://restaurant.example.ge",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    message = client.post(
        "/v1/widget/biz_1/messages",
        headers={"Origin": "https://restaurant.example.ge"},
    )

    assert preflight.status_code == 204
    assert preflight.headers["access-control-allow-origin"] == "*"
    assert message.status_code == 200
    assert message.headers["access-control-allow-origin"] == "*"


def test_cabinet_routes_keep_the_allow_list() -> None:
    client = build_client()

    allowed = client.options(
        "/v1/me",
        headers={
            "Origin": "https://cabinet.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/v1/me",
        headers={
            "Origin": "https://restaurant.example.ge",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == (
        "https://cabinet.example.com"
    )
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_only_widget_paths_answer_cors_themselves() -> None:
    assert is_self_cors_path("/v1/widget/biz_1/config")
    assert not is_self_cors_path("/v1/widgets")
    assert not is_self_cors_path("/v1/businesses/biz_1/channels/web/snippet")


class SilentErrors:
    def capture_exception(self, error: BaseException) -> None:
        del error


def build_failing_widget_client(is_cabinet_listed: bool) -> TestClient:
    router = APIRouter()

    @router.get("/v1/widget/{business_id}/config")
    def widget_config(business_id: str) -> Response:
        raise NotFoundError(f"No chat for {business_id}.")

    @router.post("/v1/widget/{business_id}/messages")
    def widget_message(business_id: str, body: WidgetBody) -> Response:
        del business_id, body
        raise RuntimeError("boom")

    @router.get("/v1/widget/{business_id}/messages")
    def widget_poll(business_id: str) -> Response:
        del business_id
        raise RateLimitedError(
            "Too many requests.", retry_after_seconds=RetryAfterSeconds(7)
        )

    application = build_http_application(
        routers=[router],
        error_reporter=SilentErrors(),
        cors_allowed_origins=(
            [PublicBaseUrl("https://cabinet.example.com")] if is_cabinet_listed else []
        ),
    )
    return TestClient(application, raise_server_exceptions=False)


@pytest.mark.parametrize("is_cabinet_listed", [True, False])
def test_widget_errors_carry_cors_headers_so_the_site_can_read_them(
    is_cabinet_listed: bool,
) -> None:
    client = build_failing_widget_client(is_cabinet_listed)
    origin = {"Origin": "https://restaurant.example.ge"}

    missing = client.get("/v1/widget/biz_1/config", headers=origin)
    invalid = client.post("/v1/widget/biz_1/messages", json={}, headers=origin)
    failed = client.post(
        "/v1/widget/biz_1/messages", json={"text": "Hello"}, headers=origin
    )
    limited = client.get("/v1/widget/biz_1/messages", headers=origin)

    assert [
        missing.status_code,
        invalid.status_code,
        failed.status_code,
        limited.status_code,
    ] == [404, 422, 500, 429]
    for response in (missing, invalid, failed, limited):
        assert response.headers["access-control-allow-origin"] == "*"
    # The widget reads how long to wait (a non-safelisted header).
    assert limited.headers["retry-after"] == "7"
    assert limited.headers["access-control-expose-headers"] == "Retry-After"
