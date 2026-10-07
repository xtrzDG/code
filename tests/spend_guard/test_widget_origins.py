"""
The websites allowed to show a business's chat: the owner's list, the check
of each widget request's page, and a foreign website refused with 403.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.operator_contract import OperatorContract
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.widget_handoff_routes import build_widget_handoff_router
from app.gateways.http.widget_origin_guard import build_widget_origin_guard
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.repositories.spend_guard_repositories import BusinessLimitsRepository
from app.schemas.constants.localization import TextDirection
from app.schemas.domain.business_limits import BusinessLimitsDocument
from app.schemas.dto.channels.widget_handoff import (
    WidgetHandoffCommand,
    WidgetHandoffView,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.spend.constrained_strings import (
    WidgetPageOrigin,
    WidgetSiteAddress,
)
from app.use_cases.spend_guard.check_widget_origin_use_case import (
    CheckWidgetOriginUseCase,
)
from app.utilities.spend.spend_keys import business_limits_id_of
from app.utilities.spend.widget_origins import (
    is_origin_allowed,
    normalize_site_address,
    page_origin_of,
    platform_page_origins,
)

BUSINESS: BusinessId = BusinessId()
CABINET: str = "https://app.workshop.example"
HANDOFF_PATH: str = f"/v1/widget/{BUSINESS}/handoff"
BODY: dict[str, str] = {"session_key": "visitor-session-0000000001"}


@pytest.mark.parametrize(
    ("typed", "origin"),
    [
        ("cafe-batumi.ge", "https://cafe-batumi.ge"),
        ("https://www.Cafe-Batumi.ge/menu?x=1", "https://www.cafe-batumi.ge"),
        ("http://localhost:8080/", "http://localhost:8080"),
        ("https://cafe-batumi.ge:443", "https://cafe-batumi.ge"),
    ],
)
def test_an_owners_address_becomes_its_origin(typed: str, origin: str) -> None:
    assert normalize_site_address(WidgetSiteAddress(typed)) == origin


@pytest.mark.parametrize("typed", ["not a site", "ftp://cafe.ge", "cafe"])
def test_what_is_not_a_website_is_refused(typed: str) -> None:
    with pytest.raises(ValidationFailedError):
        normalize_site_address(WidgetSiteAddress(typed))


def test_the_page_comes_from_origin_then_referer() -> None:
    assert page_origin_of("https://Cafe.ge", "https://other.ge/x") == "https://cafe.ge"
    assert page_origin_of(None, "https://cafe.ge/menu#top") == "https://cafe.ge"
    assert page_origin_of("null", None) == "null"
    assert page_origin_of(None, None) is None


def test_a_site_matches_with_or_without_www_and_scheme_but_not_another_port() -> None:
    allowed = [PublicBaseUrl("https://cafe.ge")]

    def allows(page: str) -> bool:
        return is_origin_allowed(WidgetPageOrigin(page), allowed, [CABINET])

    assert allows("https://www.cafe.ge")
    assert allows("http://cafe.ge")
    assert not allows("https://cafe.ge:8443")
    assert not allows("https://evil-cafe.ge")
    assert not allows("null")
    assert allows(CABINET)
    assert is_origin_allowed(WidgetPageOrigin("https://any.ge"), [], [CABINET])


def test_the_platforms_own_pages_are_the_cabinet_and_the_api() -> None:
    assert platform_page_origins(
        CABINET, "https://api.workshop.example/", ["https://app.workshop.example"]
    ) == [CABINET, "https://api.workshop.example"]


class RecordingHandoff(OperatorContract[WidgetHandoffCommand, WidgetHandoffView]):
    def __init__(self) -> None:
        self.commands: list[WidgetHandoffCommand] = []

    def operate(self, input_data: WidgetHandoffCommand) -> WidgetHandoffView:
        self.commands.append(input_data)
        return WidgetHandoffView(
            conversation_id=ConversationId(),
            is_handed_off=True,
            language=LanguageTag("en"),
            direction=TextDirection.LEFT_TO_RIGHT,
        )


def build_client(allowed: list[str]) -> tuple[TestClient, RecordingHandoff]:
    limits = BusinessLimitsRepository(
        InMemoryDocumentCollectionAdapter(BusinessLimitsDocument)
    )
    limits.save(
        BusinessLimitsDocument(
            id=business_limits_id_of(BUSINESS),
            business_id=BUSINESS,
            widget_allowed_origins=[PublicBaseUrl(origin) for origin in allowed],
        )
    )
    check = CheckWidgetOriginUseCase(limits, [PublicBaseUrl(CABINET)])
    handoff = RecordingHandoff()
    application = FastAPI()
    install_error_handlers(application)
    application.include_router(
        build_widget_handoff_router(
            handoff,
            build_widget_origin_guard(
                PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(check)))
            ),
        )
    )
    return TestClient(application), handoff


def test_a_foreign_website_is_refused_with_403() -> None:
    client, handoff = build_client(["https://cafe-batumi.ge"])

    refused = client.post(
        HANDOFF_PATH, json=BODY, headers={"Origin": "https://copycat.example"}
    )

    assert refused.status_code == 403
    assert refused.json() == {
        "error": "access_denied",
        "message": "This chat is not available on this website.",
    }
    assert handoff.commands == []


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://www.cafe-batumi.ge"},
        {"Referer": "https://cafe-batumi.ge/contacts"},
        {"Origin": CABINET},  # the hosted chat page and the preview
        {},  # no page: a server or a script, bound by the address limits
    ],
)
def test_the_businesses_own_sites_and_the_cabinet_pass(
    headers: dict[str, str],
) -> None:
    client, handoff = build_client(["https://cafe-batumi.ge"])

    response = client.post(HANDOFF_PATH, json=BODY, headers=headers)

    assert response.status_code == 200
    assert len(handoff.commands) == 1


def test_without_a_list_every_website_may_show_the_chat() -> None:
    client, _ = build_client([])

    response = client.post(
        HANDOFF_PATH, json=BODY, headers={"Origin": "https://anywhere.example"}
    )

    assert response.status_code == 200
