"""
The admin routes of the feature flags over the real use cases: GET
/v1/admin/feature-flags, PUT /v1/admin/feature-flags/{flag_name} and GET
/v1/admin/feature-flags/{flag_name}/businesses/{business_id} (REL-08).
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.contracts.use_case_contract import UseCaseContract
from app.gateways.http.admin_feature_flag_routes import (
    build_admin_feature_flag_router,
)
from app.gateways.http.error_responses import install_error_handlers
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.feature_flags.feature_flag_catalog import RELEASE_CANARY
from tests.feature_flags.flag_world import FlagWorld

PATH: str = "/v1/admin/feature-flags"
PILOT: BusinessId = BusinessId()


def operator[InputData, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
) -> PipelineOperator[InputData, OutputData]:
    return PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(use_case)))


def client_as(world: FlagWorld, user_id: UserId) -> TestClient:
    async def current_user(
        request: Request, authorization: str | None = None
    ) -> UserId:
        del request, authorization
        return user_id

    application = FastAPI()
    install_error_handlers(application)
    application.include_router(
        build_admin_feature_flag_router(
            current_user=current_user,
            list_feature_flags=operator(world.list_use_case()),
            set_feature_flag=operator(world.set_use_case()),
            check_feature_flag=operator(world.check_use_case()),
        )
    )
    return TestClient(application)


def body(percent: int = 0, **changes: Any) -> dict[str, Any]:
    return {
        "is_enabled": True,
        "rollout_percent": percent,
        "included_business_ids": [str(PILOT)],
        "excluded_business_ids": [],
        "reason": "Pilot business first",
    } | changes


def test_a_super_admin_sets_a_flag_and_support_sees_it() -> None:
    world = FlagWorld()
    admin = client_as(world, world.super_admin)
    support = client_as(world, world.support)

    changed = admin.put(f"{PATH}/release_canary", json=body(percent=10))

    assert changed.status_code == 200, changed.text
    assert changed.json()["is_enabled"] is True
    assert changed.json()["rollout_percent"] == 10
    assert changed.json()["included_business_ids"] == [str(PILOT)]
    listed = support.get(PATH)
    assert listed.status_code == 200, listed.text
    (item,) = listed.json()["items"]
    assert (item["name"], item["rollout_percent"]) == ("release_canary", 10)
    checked = support.get(f"{PATH}/release_canary/businesses/{PILOT}")
    assert checked.status_code == 200, checked.text
    assert checked.json()["is_on"] is True
    assert checked.json()["decision"] == "included"
    assert len(world.audit_entries.list_all()) == 1


def test_support_cannot_change_a_flag() -> None:
    world = FlagWorld()

    refused = client_as(world, world.support).put(
        f"{PATH}/release_canary", json=body()
    )

    assert refused.status_code == 403, refused.text
    assert world.audit_entries.list_all() == []


def test_a_stale_session_must_step_up_first() -> None:
    world = FlagWorld()
    world.step_up.is_recent = False

    refused = client_as(world, world.super_admin).put(
        f"{PATH}/release_canary", json=body()
    )

    assert refused.status_code == 401, refused.text
    assert world.flags.get(RELEASE_CANARY) is None


def test_unknown_and_malformed_names_are_not_found() -> None:
    world = FlagWorld()
    admin = client_as(world, world.super_admin)

    assert admin.put(f"{PATH}/not_registered", json=body()).status_code == 404
    assert admin.put(f"{PATH}/Not-A-Flag", json=body()).status_code == 404
    assert admin.get(f"{PATH}/release_canary/businesses/nope").status_code == 404
    assert world.audit_entries.list_all() == []


def test_bad_bodies_and_repeats_are_refused() -> None:
    world = FlagWorld()
    admin = client_as(world, world.super_admin)

    over = admin.put(f"{PATH}/release_canary", json=body(percent=101))
    both = admin.put(
        f"{PATH}/release_canary",
        json=body(excluded_business_ids=[str(PILOT)]),
    )
    short = admin.put(f"{PATH}/release_canary", json=body(reason="why"))
    first = admin.put(f"{PATH}/release_canary", json=body())
    again = admin.put(f"{PATH}/release_canary", json=body())

    assert over.status_code == 422, over.text
    assert both.status_code == 422, both.text
    assert short.status_code == 422, short.text
    assert first.status_code == 200, first.text
    assert again.status_code == 409, again.text
    assert len(world.audit_entries.list_all()) == 1
