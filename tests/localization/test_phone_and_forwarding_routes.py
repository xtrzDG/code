"""Phone number parsing and call forwarding routes."""

from fastapi.testclient import TestClient

from app.schemas.domain.businesses import BusinessDocument
from tests.localization.catalog_routes_client import (
    OWNER_TOKEN,
    STRANGER_TOKEN,
    read_json,
)


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
