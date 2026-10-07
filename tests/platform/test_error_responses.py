from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.error_responses import install_error_handlers
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ConflictError,
    ValidationFailedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage


def build_client() -> TestClient:
    http_application = FastAPI()
    install_error_handlers(http_application)

    @http_application.get("/conflict")
    def conflict() -> None:
        raise ConflictError(
            "The assistant cannot go live yet: Accept the agreement.",
            reasons=[
                ErrorReason(
                    code=ErrorReasonCode("dpa"),
                    message=ErrorReasonMessage("Accept the agreement."),
                    details=[ErrorReasonDetail("2026-10-01")],
                )
            ],
        )

    @http_application.get("/plain")
    def plain() -> None:
        raise ValidationFailedError("limit must be a whole number.")

    @http_application.get("/login")
    def login() -> None:
        raise AuthenticationRequiredError("Sign in first.")

    @http_application.get("/unknown")
    def unknown() -> None:
        raise ApplicationError("Something unexpected.")

    return TestClient(http_application)


def test_reasons_travel_in_the_error_body() -> None:
    response = build_client().get("/conflict")

    assert response.status_code == 409
    assert response.json() == {
        "error": "conflict",
        "message": "The assistant cannot go live yet: Accept the agreement.",
        "reasons": [
            {
                "code": "dpa",
                "message": "Accept the agreement.",
                "details": ["2026-10-01"],
            }
        ],
    }


def test_errors_without_reasons_keep_the_two_field_body() -> None:
    client = build_client()

    plain = client.get("/plain")
    login = client.get("/login")
    unknown = client.get("/unknown")

    assert (plain.status_code, plain.json()) == (
        422,
        {"error": "validation_failed", "message": "limit must be a whole number."},
    )
    assert login.status_code == 401
    assert login.headers["WWW-Authenticate"] == "Bearer"
    assert unknown.status_code == 500
    assert unknown.json() == {
        "error": "internal_error",
        "message": "Something unexpected.",
    }


def test_reasons_are_kept_on_the_exception() -> None:
    reason = ErrorReason(
        code=ErrorReasonCode("menu_link_unreachable"),
        message=ErrorReasonMessage("The link cannot be opened."),
    )

    error = ValidationFailedError("The menu link cannot be opened.", reasons=[reason])

    assert error.reasons == (reason,)
    assert str(error) == "The menu link cannot be opened."
    assert ConflictError("plain").reasons == ()
