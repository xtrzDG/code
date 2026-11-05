"""
Only a verified credential exempts a request from the per-address limit:
a made-up Authorization header on a route that checks no credential, or
on a path no route serves, counts like no header.
"""

from typing import Annotated

from base_pydantic_schemas import ImmutableDTO
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.gateways.http.application import build_http_application
from app.gateways.http.strict_request_parsing import build_json_body_dependency
from app.gateways.http.user_authentication import build_current_user_dependency
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.typings.platform.strings import ErrorMessageText
from app.schemas.typings.spend.constrained_integers import ApiRequestsPerMinute
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.spend_guard.admit_api_request_use_case import (
    AdmitApiRequestUseCase,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.channels.channels_fakes import FakeAuthenticationOperator
from tests.spend_guard.request_limit_app import (
    TOKEN,
    MovingClock,
    NoErrors,
    build_limited_app,
)

MADE_UP: dict[str, str] = {"Authorization": "Bearer made-up-0000"}
SIGNED_IN: dict[str, str] = {"Authorization": f"Bearer {TOKEN}"}


def test_a_made_up_header_on_a_public_route_counts_against_the_address() -> None:
    client, other_address = build_limited_app(MovingClock(), per_address=2)

    answers = [client.get("/v1/catalog/countries", headers=MADE_UP) for _ in range(3)]

    assert [answer.status_code for answer in answers] == [200, 200, 429]
    assert answers[-1].json()["error"] == "rate_limited"
    assert "Retry-After" in answers[-1].headers
    # Without the header the address is just as spent; another is not.
    assert client.get("/v1/catalog/countries").status_code == 429
    assert other_address.get("/v1/catalog/countries", headers=MADE_UP).status_code == (
        200
    )


def test_a_header_on_a_path_no_route_serves_is_counted_too() -> None:
    client, _ = build_limited_app(MovingClock(), per_address=2)

    missing = [client.get("/v1/nowhere", headers=MADE_UP) for _ in range(2)]

    assert [answer.status_code for answer in missing] == [404, 404]
    assert client.get("/v1/catalog/countries").status_code == 429


def test_a_verified_credential_still_counts_per_person_only() -> None:
    client, _ = build_limited_app(MovingClock(), per_user=10, per_address=1)

    signed_in = [client.get("/v1/me", headers=SIGNED_IN) for _ in range(4)]

    assert [answer.status_code for answer in signed_in] == [200, 200, 200, 200]
    assert client.get("/v1/catalog/countries").status_code == 200


class NoteBody(ImmutableDTO):
    note: ErrorMessageText


def build_note_app(per_address: int) -> TestClient:
    """POST /v1/notes reads its body before it checks the credential."""

    admit = AdmitApiRequestUseCase(
        rate_limit_registry=RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter()),
        settings=SpendGuardSettings(
            api_requests_per_ip_per_minute=ApiRequestsPerMinute(per_address)
        ),
        wall_clock=MovingClock().wall_clock,
    )
    current_user = build_current_user_dependency(
        FakeAuthenticationOperator(),
        SessionAssuranceContext(),
        PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(admit))),
    )
    read_note = build_json_body_dependency(NoteBody)
    router = APIRouter()

    @router.post("/v1/notes")
    def save_note(
        body: Annotated[NoteBody, Depends(read_note)],
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> dict[str, str]:
        return {"note": str(body.note), "user": str(user_id)}

    @router.get("/v1/catalog/countries")
    def countries() -> dict[str, str]:
        return {"countries": "all"}

    application = build_http_application(
        routers=[router],
        error_reporter=NoErrors(),
        cors_allowed_origins=[],
        anonymous_request_admission=admit.run,
    )
    return TestClient(application, client=("198.51.100.7", 40000))


def test_a_header_answered_before_its_credential_check_is_counted() -> None:
    client = build_note_app(per_address=2)

    refused = [
        client.post("/v1/notes", content=b"{", headers=MADE_UP) for _ in range(2)
    ]

    assert [answer.status_code for answer in refused] == [422, 422]
    assert client.get("/v1/catalog/countries").status_code == 429


def test_a_checked_header_is_counted_once_by_its_check() -> None:
    client = build_note_app(per_address=2)

    refused = client.post("/v1/notes", json={"note": "hi"}, headers=MADE_UP)

    assert refused.status_code == 401
    assert client.get("/v1/catalog/countries").status_code == 200
    assert client.get("/v1/catalog/countries").status_code == 429
