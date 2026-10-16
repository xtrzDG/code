"""Security headers of the API, and its description hidden in production."""

from fastapi import APIRouter, Response
from fastapi.testclient import TestClient

from app.gateways.http.application import build_http_application
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl


class SilentErrorReporter:
    def capture_exception(self, error: BaseException) -> None:
        del error


def build_client(
    environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT,
) -> TestClient:
    router = APIRouter()

    @router.get("/v1/me")
    def me() -> dict[str, str]:
        return {"id": "user_1"}

    @router.get("/v1/cached")
    def cached() -> Response:
        return Response("{}", headers={"Cache-Control": "public, max-age=60"})

    @router.get("/page")
    def page() -> Response:
        return Response(
            "<p>hi</p>",
            media_type="text/html",
            headers={"Content-Security-Policy": "default-src 'self'"},
        )

    @router.get("/v1/boom")
    def boom() -> None:
        raise RuntimeError("internals")

    application = build_http_application(
        routers=[router],
        error_reporter=SilentErrorReporter(),
        cors_allowed_origins=[PublicBaseUrl("https://cabinet.example.com")],
        environment=environment,
    )
    return TestClient(application, raise_server_exceptions=False)


def test_every_api_answer_carries_the_security_headers() -> None:
    response = build_client().get("/v1/me", headers={"Authorization": "Bearer x"})

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'"
    )
    assert response.headers["Cache-Control"] == "no-store"
    # Development is served over plain HTTP: no HSTS there.
    assert "Strict-Transport-Security" not in response.headers


def test_answers_keep_the_headers_they_set_themselves() -> None:
    client = build_client()

    cached = client.get("/v1/cached")
    page = client.get("/page")

    assert cached.headers["Cache-Control"] == "public, max-age=60"
    assert page.headers["Content-Security-Policy"] == "default-src 'self'"
    assert "Cache-Control" not in page.headers


def test_errors_and_cors_preflights_get_the_headers_too() -> None:
    client = build_client(DeploymentEnvironment.PRODUCTION)

    failed = client.get("/v1/boom")
    preflight = client.options(
        "/v1/me",
        headers={
            "Origin": "https://cabinet.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    for response in (failed, preflight):
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Strict-Transport-Security"] == (
            "max-age=63072000; includeSubDomains"
        )


def test_the_api_description_is_hidden_in_production() -> None:
    development = build_client()
    production = build_client(DeploymentEnvironment.PRODUCTION)

    assert development.get("/openapi.json").status_code == 200
    docs = development.get("/docs")
    assert docs.status_code == 200
    # The interactive description loads its script from a CDN.
    assert "Content-Security-Policy" not in docs.headers
    for path in ("/openapi.json", "/docs", "/redoc"):
        assert production.get(path).status_code == 404
