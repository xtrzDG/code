from dataclasses import dataclass
from typing import Any

import pytest
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
        )
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


@pytest.fixture
def fixture() -> RoutesFixture:
    return build_fixture()


def test_catalog_is_public_and_localized(fixture: RoutesFixture) -> None:
    russian = fixture.client.get("/v1/catalog/niches", params={"language": "ru"})
    georgian = fixture.client.get(
        "/v1/catalog/niches",
        headers={"Accept-Language": "ka-GE,ka;q=0.9,en;q=0.5"},
    )
    english = fixture.client.get("/v1/catalog/niches")

    assert russian.status_code == 200
    assert len(russian.json()["niches"]) == 16
    assert russian.json()["niches"][0]["name"] == "Рестораны и кафе"
    assert georgian.json()["language"] == "ka-GE"
    assert georgian.json()["niches"][0]["name"] == "რესტორნები და კაფეები"
    assert english.json()["language"] == "en"


def test_niche_details_and_unknown_niche(fixture: RoutesFixture) -> None:
    hotel = fixture.client.get("/v1/catalog/niches/hotel", params={"language": "en"})
    unknown = fixture.client.get("/v1/catalog/niches/spaceport")
    bad_language = fixture.client.get(
        "/v1/catalog/niches/hotel",
        params={"language": "12"},
    )

    assert hotel.status_code == 200
    assert hotel.json()["niche"]["booking_unit"] == "night"
    assert hotel.json()["questions"][0]["key"] == "property_type"
    assert unknown.status_code == 404
    assert bad_language.status_code == 422


def test_cabinet_routes_require_authentication_and_membership(
    fixture: RoutesFixture,
) -> None:
    anonymous = fixture.client.get(f"{fixture.base}/profile/wizard")
    stranger = fixture.client.get(f"{fixture.base}/profile/wizard", headers=STRANGER)
    staff = fixture.client.get(f"{fixture.base}/profile/wizard", headers=STAFF)
    malformed = fixture.client.get("/v1/businesses/not-an-id/profile", headers=OWNER)

    assert anonymous.status_code == 401
    assert anonymous.headers["WWW-Authenticate"] == "Bearer"
    assert stranger.status_code == 404
    assert staff.status_code == 200
    assert staff.json()["language"] == "ru"
    assert len(staff.json()["steps"]) == 6
    assert malformed.status_code == 404


def test_profile_steps_are_saved_by_owners_only(fixture: RoutesFixture) -> None:
    body: dict[str, Any] = {
        "address": {"text": "Тбилиси, Руставели 1"},
        "hours": [
            {"weekday": 5, "opens_at": 1080, "closes_at": 1440},
            {"weekday": 6, "opens_at": 0, "closes_at": 120},
        ],
        "contacts": {"handoff_phone_number": "599 12 34 56"},
    }

    by_staff = fixture.client.put(
        f"{fixture.base}/profile/steps/contacts_and_hours",
        json=body,
        headers=STAFF,
    )
    by_owner = fixture.client.put(
        f"{fixture.base}/profile/steps/contacts_and_hours",
        json=body,
        headers=OWNER,
    )
    unknown_step = fixture.client.put(
        f"{fixture.base}/profile/steps/payments",
        json=body,
        headers=OWNER,
    )

    assert by_staff.status_code == 403
    assert by_owner.status_code == 200
    assert by_owner.json()["step"] == "contacts_and_hours"
    assert by_owner.json()["profile"]["contacts"]["handoff_phone_number"] == (
        "+995599123456"
    )
    assert unknown_step.status_code == 404


@pytest.mark.parametrize(
    ("step", "body", "status_code"),
    [
        ("contacts_and_hours", {"hours": [{"weekday": 1, "opens_at": 900}]}, 422),
        (
            "contacts_and_hours",
            {"hours": [{"weekday": 1, "opens_at": 900, "closes_at": 600}]},
            422,
        ),
        ("contacts_and_hours", {"contacts": {"public_phone_number": "12"}}, 422),
        ("channels", {"links": [{"kind": "fax", "url": "https://x.example"}]}, 422),
        ("offer", {"items": [{"kind": "menu_item", "title": "Pizza"}]}, 200),
        ("booking_rules", {"booking_rules": {"max_party_size": 0}}, 422),
        ("booking_rules", {"booking_rules": {"max_party_size": 12}}, 200),
        ("niche_and_languages", {"unknown_field": True}, 422),
    ],
)
def test_step_bodies_are_validated(
    fixture: RoutesFixture,
    step: str,
    body: dict[str, Any],
    status_code: int,
) -> None:
    response = fixture.client.put(
        f"{fixture.base}/profile/steps/{step}",
        json=body,
        headers=OWNER,
    )

    assert response.status_code == status_code, response.json()
    if status_code == 422:
        assert response.json()["error"] == "validation_failed"


def test_empty_or_broken_bodies_are_validation_errors(fixture: RoutesFixture) -> None:
    empty = fixture.client.put(
        f"{fixture.base}/profile",
        content=b"",
        headers={**OWNER, "Content-Type": "application/json"},
    )
    broken = fixture.client.put(
        f"{fixture.base}/profile",
        content=b"{oops",
        headers={**OWNER, "Content-Type": "application/json"},
    )

    assert empty.status_code == 422
    assert broken.status_code == 422


def test_full_profile_read_write_and_gaps(fixture: RoutesFixture) -> None:
    blank = fixture.client.get(f"{fixture.base}/profile", headers=STAFF)
    saved = fixture.client.put(
        f"{fixture.base}/profile",
        json={
            "answers_language": "en",
            "hours": [{"weekday": 1, "opens_at": 600, "closes_at": 1320}],
            "answers": [{"question_key": "cuisine", "answer": "Georgian"}],
            "links": [{"kind": "menu", "url": "https://venue.example/menu"}],
        },
        headers=OWNER,
    )
    gaps = fixture.client.get(
        f"{fixture.base}/profile/gaps",
        params={"language": "en"},
        headers=STAFF,
    )

    assert blank.status_code == 200
    assert blank.json()["is_saved"] is False
    assert saved.status_code == 200
    assert saved.json()["is_saved"] is True
    assert saved.json()["answers_language"] == "en"
    assert gaps.status_code == 200
    kinds = [gap["kind"] for gap in gaps.json()["gaps"]]
    assert "missing_required_answer" not in kinds
    assert "no_address" in kinds
    assert gaps.json()["is_ready_for_assembly"] is False
    assert gaps.json()["gaps"][0]["description"] == "Add the address and a maps link."


def test_knowledge_crud_search_and_tenant_isolation(fixture: RoutesFixture) -> None:
    created = fixture.client.post(
        f"{fixture.base}/knowledge",
        json={
            "kind": "menu_item",
            "title": "Хачапури по-аджарски",
            "price_minor": 1800,
        },
        params={"language": "ka"},
        headers=STAFF,
    )
    item_id: str = created.json()["id"]
    listed = fixture.client.get(
        f"{fixture.base}/knowledge",
        params={"kind": "menu_item", "is_active": "true"},
        headers=OWNER,
    )
    patched = fixture.client.patch(
        f"{fixture.base}/knowledge/{item_id}",
        json={"body": "Сыр и яйцо", "is_active": True},
        headers=OWNER,
    )
    found = fixture.client.post(
        f"{fixture.base}/knowledge/search",
        json={"query": "аджарский хачапури", "language": "en", "limit": 3},
        headers=OWNER,
    )
    foreign_read = fixture.client.get(
        f"/v1/businesses/{fixture.other_business.id}/knowledge/{item_id}",
        headers=STRANGER,
    )
    deleted = fixture.client.delete(
        f"{fixture.base}/knowledge/{item_id}", headers=OWNER
    )
    missing = fixture.client.get(f"{fixture.base}/knowledge/{item_id}", headers=OWNER)

    assert created.status_code == 201
    assert created.json()["formatted_price"] == "18,00\xa0₾"
    assert created.json()["currency_code"] == "GEL"
    assert [item["id"] for item in listed.json()["items"]] == [item_id]
    assert patched.status_code == 200
    assert patched.json()["body"] == "Сыр и яйцо"
    assert found.status_code == 200
    assert found.json()["items"][0]["id"] == item_id
    assert found.json()["items"][0]["formatted_price"] == "GEL18.00"
    assert foreign_read.status_code == 404
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert missing.status_code == 404


@pytest.mark.parametrize(
    ("method", "path", "kwargs", "status_code"),
    [
        (
            "post",
            "/knowledge",
            {"json": {"kind": "menu_item", "title": "X", "currency_code": "USD"}},
            422,
        ),
        ("post", "/knowledge", {"json": {"kind": "room_type", "title": "X"}}, 422),
        ("get", "/knowledge", {"params": {"kind": "spaceship"}}, 422),
        ("get", "/knowledge", {"params": {"is_active": "maybe"}}, 422),
        ("get", "/knowledge/not-an-id", {}, 404),
        ("post", "/knowledge/search", {"json": {"query": "x", "limit": 50}}, 422),
    ],
)
def test_knowledge_errors_map_to_status_codes(
    fixture: RoutesFixture,
    method: str,
    path: str,
    kwargs: dict[str, Any],
    status_code: int,
) -> None:
    response = fixture.client.request(
        method,
        f"{fixture.base}{path}",
        headers=OWNER,
        **kwargs,
    )

    assert response.status_code == status_code, response.json()


def test_search_defaults_to_the_owner_language(fixture: RoutesFixture) -> None:
    fixture.client.post(
        f"{fixture.base}/knowledge",
        json={"kind": "menu_item", "title": "Pizza", "price_minor": 2550},
        headers=OWNER,
    )

    found = fixture.client.post(
        f"{fixture.base}/knowledge/search",
        json={"query": "pizza"},
        headers=OWNER,
    )

    assert found.json()["items"][0]["formatted_price"] == "25,50\xa0GEL"


def test_resources_and_schedule_exceptions(fixture: RoutesFixture) -> None:
    created = fixture.client.post(
        f"{fixture.base}/resources",
        json={"name": "Table 4", "capacity": 4},
        headers=STAFF,
    )
    resource_id: str = created.json()["id"]
    duplicate = fixture.client.post(
        f"{fixture.base}/resources",
        json={"name": "table 4", "capacity": 2},
        headers=STAFF,
    )
    patched = fixture.client.patch(
        f"{fixture.base}/resources/{resource_id}",
        json={"is_active": False},
        headers=OWNER,
    )
    listed = fixture.client.get(
        f"{fixture.base}/resources",
        params={"is_active": "false"},
        headers=OWNER,
    )
    holiday = fixture.client.post(
        f"{fixture.base}/schedule-exceptions",
        json={"date": "2027-01-07", "note": "Christmas"},
        headers=STAFF,
    )
    special = fixture.client.post(
        f"{fixture.base}/schedule-exceptions",
        json={
            "resource_id": resource_id,
            "date": "2026-12-31",
            "is_closed_all_day": False,
            "special_hours": [{"weekday": 4, "opens_at": 720, "closes_at": 1440}],
        },
        headers=STAFF,
    )
    for_resource = fixture.client.get(
        f"{fixture.base}/schedule-exceptions",
        params={"resource_id": resource_id, "from_date": "2026-12-01"},
        headers=OWNER,
    )
    past = fixture.client.post(
        f"{fixture.base}/schedule-exceptions",
        json={"date": "2026-01-01"},
        headers=OWNER,
    )
    bad_filter = fixture.client.get(
        f"{fixture.base}/schedule-exceptions",
        params={"from_date": "01.12.2026"},
        headers=OWNER,
    )
    deleted = fixture.client.delete(
        f"{fixture.base}/schedule-exceptions/{holiday.json()['id']}",
        headers=OWNER,
    )
    foreign_patch = fixture.client.patch(
        f"/v1/businesses/{fixture.other_business.id}/resources/{resource_id}",
        json={"is_active": True},
        headers=STRANGER,
    )

    assert created.status_code == 201
    assert created.json()["kind"] == "table"
    assert duplicate.status_code == 409
    assert patched.json()["is_active"] is False
    assert [item["id"] for item in listed.json()["items"]] == [resource_id]
    assert holiday.status_code == 201
    assert holiday.json()["weekday"] == 4
    assert special.status_code == 201
    assert [item["date"] for item in for_resource.json()["items"]] == [
        "2026-12-31",
        "2027-01-07",
    ]
    assert past.status_code == 422
    assert bad_filter.status_code == 422
    assert deleted.status_code == 204
    assert foreign_patch.status_code == 404


def test_openapi_documents_json_request_bodies(fixture: RoutesFixture) -> None:
    schema = fixture.client.get("/openapi.json").json()

    knowledge_post = schema["paths"]["/v1/businesses/{business_id}/knowledge"]["post"]
    step_put = schema["paths"]["/v1/businesses/{business_id}/profile/steps/{step}"][
        "put"
    ]
    body_schema = knowledge_post["requestBody"]["content"]["application/json"]["schema"]

    assert body_schema["$id"].endswith("KnowledgeItemInput")
    assert (
        len(step_put["requestBody"]["content"]["application/json"]["schema"]["oneOf"])
        == 6
    )
