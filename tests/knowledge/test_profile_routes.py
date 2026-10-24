"""Catalog and profile routes: public catalog, membership, step saves, validation."""

from typing import Any

import pytest

from tests.knowledge.routes_fixture import OWNER, STAFF, STRANGER, RoutesFixture


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
