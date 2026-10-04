"""The catalog routes on a small app with token login, and a JSON reader."""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.catalog_routes import build_catalog_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from app.use_cases.catalog.get_country_profile_use_case import GetCountryProfileUseCase
from app.use_cases.catalog.list_countries_use_case import ListCountriesUseCase
from app.use_cases.catalog.list_languages_use_case import ListLanguagesUseCase
from app.use_cases.catalog.quote_plans_use_case import QuotePlansUseCase
from app.use_cases.localization.parse_phone_number_use_case import (
    ParsePhoneNumberUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.billing.exchange_rate_fixtures import rate_registry
from tests.foundation.access_support import signed_in
from tests.localization.builders import (
    JULY_2026_NANOSECONDS,
    build_business,
    build_wall_clock,
    get_country_registry,
    get_language_registry,
)
from tests.localization.cabinet_builders import add_phone_channel, build_cabinet_world

OWNER_TOKEN: str = "owner-token"


STRANGER_TOKEN: str = "stranger-token"


class TokenTableAuthenticationOperator(OperatorContract[AccessToken, SessionAssurance]):
    """Fake authentication: a fixed token -> user table."""

    def __init__(self, users_by_token: dict[str, UserId]) -> None:
        self._users_by_token: dict[str, UserId] = users_by_token

    def operate(self, input_data: AccessToken) -> SessionAssurance:
        user_id: UserId | None = self._users_by_token.get(str(input_data))
        if user_id is None:
            raise AuthenticationRequiredError("Session is not valid.")

        return signed_in(user_id)


def build_client() -> tuple[TestClient, BusinessDocument]:
    country_registry = get_country_registry()
    language_registry = get_language_registry()
    world = build_cabinet_world()
    owner_id = UserId()
    business = build_business(owner_id, "GE", "ka")
    world.business_repo.save(business)
    add_phone_channel(world, business, "+995322123456")
    current_user = build_current_user_dependency(
        TokenTableAuthenticationOperator(
            {OWNER_TOKEN: owner_id, STRANGER_TOKEN: UserId()}
        ),
        SessionAssuranceContext(),
    )
    router = build_catalog_router(
        list_countries_operator=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(ListCountriesUseCase(country_registry))
            )
        ),
        get_country_profile_operator=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    GetCountryProfileUseCase(
                        country_registry=country_registry,
                        language_registry=language_registry,
                        wall_clock=build_wall_clock(JULY_2026_NANOSECONDS),
                    )
                )
            )
        ),
        list_languages_operator=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(ListLanguagesUseCase(language_registry))
            )
        ),
        quote_plans_operator=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    QuotePlansUseCase(
                        plan_registry=PlanRegistry(),
                        country_registry=country_registry,
                        exchange_rate_registry=rate_registry(),
                        localized_text_resolver=LocalizedTextResolver(),
                    )
                )
            )
        ),
        parse_phone_number_operator=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(ParsePhoneNumberUseCase(PhoneNumberParser()))
            )
        ),
        call_forwarding_instructions_operator=world.call_forwarding_operator,
        current_user=current_user,
    )
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(router)
    return TestClient(http_application), business


def read_json(response: Any) -> Any:
    return response.json()
