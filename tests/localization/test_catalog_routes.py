from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.catalog_routes import build_catalog_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from app.use_cases.catalog.get_country_profile_use_case import (
    GetCountryProfileUseCase,
)
from app.use_cases.catalog.list_countries_use_case import ListCountriesUseCase
from app.use_cases.catalog.list_languages_use_case import ListLanguagesUseCase
from app.use_cases.catalog.quote_plans_use_case import QuotePlansUseCase
from app.use_cases.localization.parse_phone_number_use_case import (
    ParsePhoneNumberUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.localization.phone_number_parser import PhoneNumberParser
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


class TokenTableAuthenticationOperator(OperatorContract[AccessToken, UserId]):
    """Fake authentication: a fixed token -> user table."""

    def __init__(self, users_by_token: dict[str, UserId]) -> None:
        self._users_by_token: dict[str, UserId] = users_by_token

    def operate(self, input_data: AccessToken) -> UserId:
        user_id: UserId | None = self._users_by_token.get(str(input_data))
        if user_id is None:
            raise AuthenticationRequiredError("Session is not valid.")

        return user_id


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
        )
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
                        exchange_rate_registry=ExchangeRateRegistry(),
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


@pytest.fixture(name="client_and_business")
def fixture_client_and_business() -> tuple[TestClient, BusinessDocument]:
    return build_client()


@pytest.fixture(name="client")
def fixture_client(
    client_and_business: tuple[TestClient, BusinessDocument],
) -> TestClient:
    return client_and_business[0]


def read_json(response: Any) -> Any:
    return response.json()


def test_countries_are_listed_in_the_requested_language(client: TestClient) -> None:
    response = client.get("/v1/catalog/countries", params={"language": "ka"})

    assert response.status_code == 200
    body = read_json(response)
    assert body["display_language"] == "ka"
    assert len(body["countries"]) >= 200
    georgia = next(c for c in body["countries"] if c["country_code"] == "GE")
    assert georgia["display_name"] == "საქართველო"
    assert georgia["calling_code"] == 995
    assert georgia["onboarding_status"] == "pilot"


def test_language_defaults_to_english_and_is_normalized(client: TestClient) -> None:
    default_response = client.get("/v1/catalog/countries")
    normalized_response = client.get(
        "/v1/catalog/countries", params={"language": "PT_br"}
    )

    assert read_json(default_response)["display_language"] == "en"
    assert read_json(normalized_response)["display_language"] == "pt-BR"


@pytest.mark.parametrize("language", ["english", "xx", "en-US-x-private"])
def test_bad_language_is_a_validation_error(client: TestClient, language: str) -> None:
    response = client.get("/v1/catalog/countries", params={"language": language})

    assert response.status_code == 422
    assert read_json(response)["error"] == "validation_failed"


def test_country_profile_route_accepts_lowercase_codes(client: TestClient) -> None:
    response = client.get("/v1/catalog/countries/ge", params={"language": "ru"})

    assert response.status_code == 200
    body = read_json(response)
    assert body["display_name"] == "Грузия"
    assert body["profile"]["currency_code"] == "GEL"
    assert body["profile"]["default_customer_languages"] == ["ka", "ru", "en"]
    assert body["profile"]["on_request_customer_languages"] == ["tr", "he", "ar", "hy"]
    assert body["default_timezone"]["display_name"] == "Asia/Tbilisi (UTC+04:00)"
    hebrew = next(
        option
        for option in body["on_request_customer_languages"]
        if option["tag"] == "he"
    )
    assert hebrew["direction"] == "rtl"
    assert hebrew["native_name"] == "עברית"


@pytest.mark.parametrize("country_code", ["ZZ", "GEO", "1"])
def test_unknown_country_is_a_validation_error(
    client: TestClient, country_code: str
) -> None:
    response = client.get(f"/v1/catalog/countries/{country_code}")

    assert response.status_code == 422


def test_languages_route_lists_right_to_left_languages(client: TestClient) -> None:
    response = client.get("/v1/catalog/languages", params={"language": "he"})

    assert response.status_code == 200
    by_tag = {item["profile"]["tag"]: item for item in read_json(response)["languages"]}
    assert by_tag["ar"]["profile"]["direction"] == "rtl"
    assert by_tag["ka"]["profile"]["voice_support"] == "needs_pilot_check"
    assert by_tag["he"]["display_name"] == "עברית"


def test_plans_route_quotes_lari_for_georgia_and_no_dollars_for_the_usa(
    client: TestClient,
) -> None:
    georgia = read_json(
        client.get("/v1/catalog/plans", params={"country_code": "GE", "language": "ru"})
    )
    usa = read_json(client.get("/v1/catalog/plans", params={"country_code": "us"}))

    voice = next(q for q in georgia["quotes"] if q["plan_key"] == "voice_and_chat")
    assert voice["name"] == "Голос + чат"
    assert voice["local_monthly_price"]["money"] == {
        "amount_minor": 51700,
        "currency_code": "GEL",
    }
    assert voice["local_monthly_price"]["is_estimated"] is False
    assert georgia["exchange_rate"]["rate"] == 2.9552
    assert usa["local_currency_code"] == "USD"
    assert all(quote["local_monthly_price"] is None for quote in usa["quotes"])
    assert usa["exchange_rate"] is None


def test_plans_route_requires_a_country(client: TestClient) -> None:
    assert client.get("/v1/catalog/plans").status_code == 422


def test_phone_number_parsing_route(client: TestClient) -> None:
    response = client.post(
        "/v1/phone-numbers/parse",
        json={"raw_phone_number": "8 (999) 123-45-67", "country_hint": "RU"},
    )
    international = client.post(
        "/v1/phone-numbers/parse",
        json={"raw_phone_number": "+972 50-234-5678"},
    )

    assert response.status_code == 200
    body = read_json(response)
    assert body["e164"] == "+79991234567"
    assert body["country_code"] == "RU"
    assert body["kind"] == "mobile"
    assert read_json(international)["country_code"] == "IL"


def test_invalid_phone_number_is_a_validation_error_without_echo(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/phone-numbers/parse",
        json={"raw_phone_number": "call me 555-PRIVATE", "country_hint": "GE"},
    )

    assert response.status_code == 422
    assert read_json(response)["error"] == "validation_failed"
    assert "PRIVATE" not in response.text


def test_phone_number_hint_must_be_an_upper_case_code(client: TestClient) -> None:
    response = client.post(
        "/v1/phone-numbers/parse",
        json={"raw_phone_number": "555 12 34 56", "country_hint": "georgia"},
    )

    assert response.status_code == 422


def test_call_forwarding_route_requires_a_member(
    client_and_business: tuple[TestClient, BusinessDocument],
) -> None:
    client, business = client_and_business
    path = f"/v1/businesses/{business.id}/call-forwarding-instructions"

    owner_response = client.get(
        path, headers={"Authorization": f"Bearer {OWNER_TOKEN}"}
    )
    russian_response = client.get(
        path,
        params={"language": "ru"},
        headers={"Authorization": f"Bearer {OWNER_TOKEN}"},
    )
    anonymous_response = client.get(path)
    stranger_response = client.get(
        path, headers={"Authorization": f"Bearer {STRANGER_TOKEN}"}
    )
    malformed_id_response = client.get(
        "/v1/businesses/not-a-business/call-forwarding-instructions",
        headers={"Authorization": f"Bearer {OWNER_TOKEN}"},
    )

    assert owner_response.status_code == 200
    body = read_json(owner_response)
    assert body["display_language"] == "ka"
    assert body["codes"][0] == {
        "condition": "no_answer",
        "dial_code": "**61*+995322123456#",
        "description": "იმ ზარების გადამისამართება, რომლებსაც არ უპასუხეთ.",
    }
    assert [carrier["carrier_name"] for carrier in body["carriers"]] == [
        "Magti",
        "Silknet",
        "Cellfie",
    ]
    assert read_json(russian_response)["steps"][1].startswith("Наберите **61*")
    assert anonymous_response.status_code == 401
    assert stranger_response.status_code == 404
    assert malformed_id_response.status_code == 404
