from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.gateways.http.application import build_http_application, sanitize_request_id
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl


class RecordingErrorReporter:
    def __init__(self) -> None:
        self.errors: list[BaseException] = []

    def capture_exception(self, error: BaseException) -> None:
        self.errors.append(error)


def build_client() -> tuple[TestClient, RecordingErrorReporter]:
    router = APIRouter()

    @router.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internals")

    @router.get("/taken")
    def taken() -> None:
        raise ConflictError("Slot is already taken.")

    reporter = RecordingErrorReporter()
    application = build_http_application(
        routers=[router],
        error_reporter=reporter,
        cors_allowed_origins=[PublicBaseUrl("https://cabinet.example.com")],
    )
    return TestClient(application, raise_server_exceptions=False), reporter


def test_health_and_request_id() -> None:
    client, _ = build_client()

    response = client.get("/healthz", headers={"X-Request-ID": "req-42"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "req-42"
    generated = client.get("/healthz").headers["X-Request-ID"]
    assert len(generated) == 36


def test_errors_map_to_status_codes_without_internals() -> None:
    client, reporter = build_client()

    conflict = client.get("/taken")
    unexpected = client.get("/boom")

    assert conflict.status_code == 409
    assert conflict.json() == {"error": "conflict", "message": "Slot is already taken."}
    assert unexpected.status_code == 500
    assert "secret" not in unexpected.text
    assert [type(error) for error in reporter.errors] == [RuntimeError]


def test_cors_allows_the_cabinet_origin_only() -> None:
    client, _ = build_client()

    allowed = client.options(
        "/healthz",
        headers={
            "Origin": "https://cabinet.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/healthz",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.headers.get("access-control-allow-origin") == (
        "https://cabinet.example.com"
    )
    assert "access-control-allow-origin" not in denied.headers


def test_request_id_sanitizing() -> None:
    assert sanitize_request_id("abc-123") == "abc-123"
    assert sanitize_request_id("x" * 500) != "x" * 500
    assert sanitize_request_id("bad\nid") != "bad\nid"
    assert len(sanitize_request_id(None)) == 36
