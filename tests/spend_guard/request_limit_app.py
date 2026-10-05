"""
A small API with the generic request limits: a signed-in route, an export
route, a public route and a widget route, over in-memory rate-limit
buckets and a clock the tests move.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from typed_time_provider import Microseconds, WallClock

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.gateways.http.application import build_http_application
from app.gateways.http.user_authentication import build_current_user_dependency
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.spend.constrained_integers import ApiRequestsPerMinute
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.spend_guard.admit_api_request_use_case import (
    AdmitApiRequestUseCase,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.channels.channels_fakes import FakeAuthenticationOperator

START: int = 1_791_187_200_000_000  # 2026-10-05 08:00 UTC
OWNER: UserId = UserId()
TOKEN: str = "test-token-0000"


class MovingClock:
    def __init__(self) -> None:
        self.now: int = START
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self.now * 1_000,
        )


class NoErrors:
    def capture_exception(self, error: BaseException) -> None:
        raise AssertionError(error)


def build_limited_app(
    clock: MovingClock, per_user: int = 3, exports: int = 1, per_address: int = 2
) -> tuple[TestClient, TestClient]:
    """Clients from two addresses (198.51.100.7 and 203.0.113.9)."""

    admit = AdmitApiRequestUseCase(
        rate_limit_registry=RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter()),
        settings=SpendGuardSettings(
            api_requests_per_user_per_minute=ApiRequestsPerMinute(per_user),
            api_exports_per_user_per_minute=ApiRequestsPerMinute(exports),
            api_requests_per_ip_per_minute=ApiRequestsPerMinute(per_address),
        ),
        wall_clock=clock.wall_clock,
    )
    authentication = FakeAuthenticationOperator()
    authentication.users_by_token[TOKEN] = OWNER
    current_user = build_current_user_dependency(
        authentication,
        SessionAssuranceContext(),
        PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(admit))),
    )
    router = APIRouter()

    @router.get("/v1/me")
    def me(user_id: Annotated[UserId, Depends(current_user)]) -> dict[str, str]:
        return {"user": str(user_id)}

    @router.get("/v1/businesses/b/exports/bookings")
    def export(user_id: Annotated[UserId, Depends(current_user)]) -> dict[str, str]:
        return {"user": str(user_id)}

    @router.get("/v1/catalog/countries")
    def countries() -> dict[str, str]:
        return {"countries": "all"}

    @router.get("/v1/widget/b/config")
    def widget() -> dict[str, str]:
        return {"widget": "on"}

    application = build_http_application(
        routers=[router],
        error_reporter=NoErrors(),
        cors_allowed_origins=[PublicBaseUrl("https://cabinet.example.com")],
        anonymous_request_admission=admit.run,
    )
    return (
        TestClient(application, client=("198.51.100.7", 40000)),
        TestClient(application, client=("203.0.113.9", 40000)),
    )
