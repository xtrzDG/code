"""
The admin routes of the platform's brakes and the payment reconciliation
over the real use cases: GET and PUT /v1/admin/platform/pause, GET
/v1/admin/payments/reconciliation.
"""

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.use_case_contract import UseCaseContract
from app.gateways.http.admin_platform_safety_routes import (
    build_admin_platform_safety_router,
)
from app.gateways.http.error_responses import install_error_handlers
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.repositories.business_repositories import BusinessRepository
from app.repositories.platform_safety_repositories import (
    PaymentReconciliationRepository,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payment_reconciliations import PaymentReconciliationDocument
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.billing.reconciliation.get_payment_reconciliation_use_case import (
    GetPaymentReconciliationUseCase,
)
from tests.spend_guard.platform_pause_world import PauseWorld


def operator[InputData, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
) -> PipelineOperator[InputData, OutputData]:
    return PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(use_case)))


def client_as(world: PauseWorld, user_id: UserId) -> TestClient:
    async def current_user(
        request: Request, authorization: str | None = None
    ) -> UserId:
        del request, authorization
        return user_id

    reconciliation = GetPaymentReconciliationUseCase(
        world.admins(),
        PaymentReconciliationRepository(
            InMemoryDocumentCollectionAdapter(PaymentReconciliationDocument)
        ),
        BusinessRepository(InMemoryDocumentCollectionAdapter(BusinessDocument)),
        world.wall_clock(),
    )
    application = FastAPI()
    install_error_handlers(application)
    application.include_router(
        build_admin_platform_safety_router(
            current_user=current_user,
            get_platform_pause=operator(world.get_use_case()),
            set_platform_pause=operator(world.set_use_case()),
            get_payment_reconciliation=operator(reconciliation),
        )
    )
    return TestClient(application)


def test_a_super_admin_pauses_through_the_api_and_everyone_sees_it() -> None:
    world = PauseWorld()
    admin = client_as(world, world.super_admin)

    paused = admin.put(
        "/v1/admin/platform/pause",
        json={"is_paused": True, "reason": "Prompt injection wave, stop now"},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )

    assert paused.status_code == 200, paused.text
    assert paused.json()["is_paused"] is True
    assert paused.json()["brake"] == "paused"
    seen = client_as(world, world.support).get("/v1/admin/platform/pause")
    assert seen.status_code == 200
    assert seen.json()["reason"] == "Prompt injection wave, stop now"
    again = admin.put(
        "/v1/admin/platform/pause",
        json={"is_paused": True, "reason": "Prompt injection wave, stop now"},
    )
    assert again.status_code == 409


def test_the_pause_needs_a_super_admin_and_a_real_reason() -> None:
    world = PauseWorld()

    refused = client_as(world, world.support).put(
        "/v1/admin/platform/pause", json={"is_paused": True, "reason": "Long enough"}
    )
    short = client_as(world, world.super_admin).put(
        "/v1/admin/platform/pause", json={"is_paused": True, "reason": "no"}
    )

    assert refused.status_code == 403
    assert short.status_code == 422
    assert world.pauses.get() is None


def test_the_reconciliation_is_for_billing_and_super_admins() -> None:
    world = PauseWorld()

    empty = client_as(world, world.billing).get("/v1/admin/payments/reconciliation")
    refused = client_as(world, world.support).get("/v1/admin/payments/reconciliation")

    assert empty.status_code == 200
    assert empty.json()["mismatches"] == [] and empty.json()["day"] is None
    assert refused.status_code == 403
