"""
Every security line names its actor (LOG-01): the signed-in person's
pseudonymous user id once the request's token was accepted, `anonymous`
for a request without one, `system` for work outside any request.
"""

import logging

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.gateways.http.application import build_http_application
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    AuthenticationRequiredError,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.observability.request_origin import (
    ANONYMOUS_ACTOR,
    SYSTEM_ACTOR,
    bound_request_origin,
    current_request_origin,
    current_security_actor,
    note_request_actor,
)
from app.utilities.observability.security_events import (
    AUTHORIZATION_DENIED,
    log_security_event,
)

PERSON: UserId = UserId()


class SilentErrorReporter:
    def capture_exception(self, error: BaseException) -> None:
        del error


def build_client() -> TestClient:
    router = APIRouter()

    @router.get("/v1/me")
    def me() -> None:
        raise AuthenticationRequiredError("The session is invalid.")

    @router.get("/v1/businesses/{business_id}/settings")
    def settings(business_id: str) -> None:
        del business_id
        # What the bearer-token dependency does once the token is accepted.
        note_request_actor(PERSON)
        raise AccessDeniedError("Owners only.")

    application = build_http_application(
        routers=[router], error_reporter=SilentErrorReporter(), cors_allowed_origins=[]
    )
    return TestClient(application, client=("203.0.113.77", 40000))


def actors(caplog: pytest.LogCaptureFixture) -> list[object]:
    return [
        dict(record.__dict__["log_fields"]).get("actor")
        for record in caplog.records
        if record.name == "app.security"
    ]


def test_a_refused_request_names_who_made_it(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="app.security")
    client = build_client()

    unauthenticated = client.get("/v1/me")
    forbidden = client.get("/v1/businesses/business_1/settings")

    assert (unauthenticated.status_code, forbidden.status_code) == (401, 403)
    assert actors(caplog) == [ANONYMOUS_ACTOR, str(PERSON)]
    # The actor is a pseudonym: never the address the request came from.
    assert "203.0.113.77" not in caplog.text


def test_work_outside_a_request_is_the_systems(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger="app.security")

    log_security_event(
        AUTHORIZATION_DENIED, path="queued_job:x", reason="r", client_address=None
    )

    assert actors(caplog) == [SYSTEM_ACTOR]


def test_the_actor_is_kept_only_inside_its_request() -> None:
    with bound_request_origin("198.51.100.1", None) as origin:
        assert current_security_actor() == ANONYMOUS_ACTOR
        note_request_actor(PERSON)
        assert current_security_actor() == str(PERSON)
        assert current_request_origin() is origin

    assert current_request_origin() is None
    assert current_security_actor() == SYSTEM_ACTOR
    # Noting an actor outside a request changes nothing.
    note_request_actor(PERSON)
    assert current_security_actor() == SYSTEM_ACTOR


@pytest.mark.parametrize("address", [None, ""])
def test_a_request_without_a_client_address_has_none(address: str | None) -> None:
    with bound_request_origin(address, "curl/8.9") as origin:
        assert origin.client_ip_address is None
        assert str(origin.user_agent) == "curl/8.9"
