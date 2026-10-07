"""The knowledge, profile and resource routes on a small app with token login."""

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contracts.operator_contract import OperatorContract
from app.contracts.use_case_contract import UseCaseContract
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.knowledge_routes import build_knowledge_router
from app.gateways.http.profile_routes import build_profile_router
from app.gateways.http.resource_routes import build_resource_router
from app.gateways.http.user_authentication import build_current_user_dependency
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.knowledge.fakes import FakeUserAuthenticationOperator
from tests.knowledge.harness import KnowledgeHarness

OWNER: dict[str, str] = {"Authorization": "Bearer owner-token"}


STAFF: dict[str, str] = {"Authorization": "Bearer staff-token"}


STRANGER: dict[str, str] = {"Authorization": "Bearer stranger-token"}


def operator[InputData, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
) -> OperatorContract[InputData, OutputData]:
    return PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(use_case)))


@dataclass
class RoutesFixture:
    client: TestClient
    harness: KnowledgeHarness
    business: BusinessDocument
    other_business: BusinessDocument

    @property
    def base(self) -> str:
        return f"/v1/businesses/{self.business.id}"


def build_fixture(niche_key: NicheKey = NicheKey.RESTAURANT) -> RoutesFixture:
    harness = KnowledgeHarness()
    owner_id, staff_id, stranger_id = UserId(), UserId(), UserId()
    business = harness.add_business(
        niche_key=niche_key,
        owner_id=owner_id,
        staff_ids=(staff_id,),
        owner_language="ru",
    )
    other_business = harness.add_business(owner_id=stranger_id)
    current_user = build_current_user_dependency(
        FakeUserAuthenticationOperator(
            {
                "owner-token": owner_id,
                "staff-token": staff_id,
                "stranger-token": stranger_id,
            }
        ),
        SessionAssuranceContext(),
    )
    access_operator = operator(harness.authorize_business_access)
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(
        build_profile_router(
            current_user=current_user,
            business_access_operator=access_operator,
            list_niche_templates_operator=operator(harness.list_niche_templates),
            get_niche_template_operator=operator(harness.get_niche_template),
            get_profile_wizard_operator=operator(harness.get_profile_wizard),
            get_business_profile_operator=operator(harness.get_business_profile),
            save_profile_operator=operator(harness.save_profile),
            save_profile_step_operator=operator(harness.save_profile_step),
            compute_profile_gaps_operator=operator(harness.compute_profile_gaps),
        )
    )
    http_application.include_router(
        build_knowledge_router(
            current_user=current_user,
            business_access_operator=access_operator,
            list_knowledge_items_operator=operator(harness.list_knowledge_items),
            create_knowledge_item_operator=operator(harness.create_knowledge_item),
            get_knowledge_item_operator=operator(harness.get_knowledge_item),
            update_knowledge_item_operator=operator(harness.update_knowledge_item),
            delete_knowledge_item_operator=operator(harness.delete_knowledge_item),
            search_knowledge_operator=operator(harness.search_knowledge),
        )
    )
    http_application.include_router(
        build_resource_router(
            current_user=current_user,
            business_access_operator=access_operator,
            list_resources_operator=operator(harness.list_resources),
            create_resource_operator=operator(harness.create_resource),
            update_resource_operator=operator(harness.update_resource),
            list_schedule_exceptions_operator=operator(
                harness.list_schedule_exceptions
            ),
            create_schedule_exception_operator=operator(
                harness.create_schedule_exception
            ),
            delete_schedule_exception_operator=operator(
                harness.delete_schedule_exception
            ),
        )
    )
    return RoutesFixture(
        client=TestClient(http_application),
        harness=harness,
        business=business,
        other_business=other_business,
    )
