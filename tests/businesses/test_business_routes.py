from typing import Any

from fastapi.testclient import TestClient

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from tests.users.accounts_testbed import (
    GEORGIA_MOBILE,
    GERMANY_MOBILE,
    ISRAEL_MOBILE,
    AccountsTestbed,
    bearer,
    build_accounts_testbed,
)


def signed_in(testbed: AccountsTestbed, raw_phone_number: str) -> dict[str, str]:
    return bearer(testbed.sign_in_with_phone(raw_phone_number).access_token)


def create_business(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.post(
        "/v1/businesses",
        headers=headers,
        json={"name": "Funicular VR", "niche_key": "entertainment", "city": "Tbilisi"},
    )
    assert response.status_code == 201
    business: dict[str, Any] = response.json()
    return business


def test_owner_creates_lists_reads_and_updates_a_business() -> None:
    testbed = build_accounts_testbed()
    client = testbed.build_http_client()
    owner = signed_in(testbed, GEORGIA_MOBILE)

    business = create_business(client, owner)
    assert business["country_code"] == "GE"
    assert business["currency_code"] == "GEL"
    assert business["timezone"] == "Asia/Tbilisi"
    assert business["languages"] == ["ka", "ru", "en"]
    assert business["plan_key"] == "chat"
    assert business["viewer_role"] == "owner"
    assert business["status"] == "onboarding"

    listed = client.get("/v1/businesses", headers=owner)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [business["id"]]

    fetched = client.get(f"/v1/businesses/{business['id']}", headers=owner)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Funicular VR"

    patched = client.patch(
        f"/v1/businesses/{business['id']}",
        headers=owner,
        json={
            "languages": ["ka", "en", "he"],
            "default_language": "en",
            "recording_retention_days": 30,
            "plan_key": "voice_and_chat",
            "manager_contacts": [
                {"name": "Levan", "channel": "whatsapp", "address": "599 12 34 56"},
                {
                    "name": "Dana",
                    "channel": "email",
                    "address": "Dana@Example.com",
                    "language": "he",
                },
            ],
        },
    )
    assert patched.status_code == 200
    body: dict[str, Any] = patched.json()
    assert body["languages"] == ["ka", "en", "he"]
    assert body["default_language"] == "en"
    assert body["recording_retention_days"] == 30
    assert body["plan_key"] == "voice_and_chat"
    assert body["manager_contacts"] == [
        {
            "name": "Levan",
            "channel": "whatsapp",
            "address": "+995599123456",
            "language": "ka",
        },
        {
            "name": "Dana",
            "channel": "email",
            "address": "dana@example.com",
            "language": "he",
        },
    ]


def test_team_routes_invite_and_remove_staff() -> None:
    testbed = build_accounts_testbed()
    client = testbed.build_http_client()
    owner = signed_in(testbed, GEORGIA_MOBILE)
    business = create_business(client, owner)

    invited = client.post(
        f"/v1/businesses/{business['id']}/members",
        headers=owner,
        json={"phone_number": ISRAEL_MOBILE, "display_name": "Tamar"},
    )
    assert invited.status_code == 201
    staff_member = invited.json()["members"][1]
    assert staff_member["role"] == "staff"
    assert staff_member["phone_number"] == "+972502345678"

    staff = signed_in(testbed, ISRAEL_MOBILE)
    staff_patch = client.patch(
        f"/v1/businesses/{business['id']}",
        headers=staff,
        json={"name": "Taken over"},
    )
    staff_read = client.get(f"/v1/businesses/{business['id']}", headers=staff)
    assert staff_patch.status_code == 403
    assert staff_read.status_code == 200
    assert staff_read.json()["viewer_role"] == "staff"

    removed = client.delete(
        f"/v1/businesses/{business['id']}/members/{staff_member['user_id']}",
        headers=owner,
    )
    assert removed.status_code == 200
    assert len(removed.json()["members"]) == 1

    last_owner = client.delete(
        f"/v1/businesses/{business['id']}/members/{business['members'][0]['user_id']}",
        headers=owner,
    )
    assert last_owner.status_code == 409
    demoted_last_owner = client.patch(
        f"/v1/businesses/{business['id']}/members/{business['members'][0]['user_id']}",
        headers=owner,
        json={"role": "staff"},
    )
    assert demoted_last_owner.status_code == 409
    assert client.get(
        f"/v1/businesses/{business['id']}", headers=staff
    ).status_code == (404)


def test_business_routes_report_errors_with_status_codes() -> None:
    testbed = build_accounts_testbed()
    client = testbed.build_http_client()
    owner = signed_in(testbed, GEORGIA_MOBILE)
    stranger = signed_in(testbed, GERMANY_MOBILE)
    business = create_business(client, owner)
    business_url = f"/v1/businesses/{business['id']}"

    responses = {
        "no token": client.get("/v1/businesses"),
        "malformed id": client.get("/v1/businesses/not-an-id", headers=owner),
        "unknown business": client.get(
            f"/v1/businesses/{BusinessId()}",
            headers=owner,
        ),
        "foreign business": client.get(business_url, headers=stranger),
        "retention out of range": client.patch(
            business_url,
            headers=owner,
            json={"recording_retention_days": 0},
        ),
        "unknown niche": client.post(
            "/v1/businesses",
            headers=owner,
            json={"name": "X", "niche_key": "spaceport"},
        ),
        "restricted country": client.post(
            "/v1/businesses",
            headers=owner,
            json={"name": "X", "niche_key": "restaurant", "country_code": "KP"},
        ),
        "status not allowed": client.patch(
            business_url,
            headers=owner,
            json={"status": BusinessStatus.LIVE.value},
        ),
        "malformed member id": client.delete(
            f"{business_url}/members/nobody",
            headers=owner,
        ),
        "unknown member": client.delete(
            f"{business_url}/members/{UserId()}",
            headers=owner,
        ),
        "invalid telegram id": client.patch(
            business_url,
            headers=owner,
            json={
                "manager_contacts": [
                    {"name": "Bot", "channel": "telegram", "address": "@bot"}
                ]
            },
        ),
    }

    assert {name: response.status_code for name, response in responses.items()} == {
        "no token": 401,
        "malformed id": 404,
        "unknown business": 404,
        "foreign business": 404,
        "retention out of range": 422,
        "unknown niche": 422,
        "restricted country": 403,
        "status not allowed": 409,
        "malformed member id": 404,
        "unknown member": 404,
        "invalid telegram id": 422,
    }


def test_team_routes_invite_an_owner_and_change_roles() -> None:
    testbed = build_accounts_testbed()
    client = testbed.build_http_client()
    owner = signed_in(testbed, GEORGIA_MOBILE)
    business = create_business(client, owner)
    members_path = f"/v1/businesses/{business['id']}/members"

    invited = client.post(
        members_path,
        headers=owner,
        json={"email": "partner@example.com", "role": "owner"},
    )
    partner = invited.json()["members"][1]
    demoted = client.patch(
        f"{members_path}/{partner['user_id']}",
        headers=owner,
        json={"role": "staff"},
    )
    bad_role = client.patch(
        f"{members_path}/{partner['user_id']}",
        headers=owner,
        json={"role": "manager"},
    )
    unknown = client.patch(
        f"{members_path}/User_9350a036-5dd7-4608-addd-224843d592d8",
        headers=owner,
        json={"role": "owner"},
    )

    assert invited.status_code == 201
    assert partner["role"] == "owner"
    assert demoted.status_code == 200
    assert demoted.json()["members"][1]["role"] == "staff"
    assert bad_role.status_code == 422
    assert unknown.status_code == 404


def test_a_settings_save_from_an_older_revision_is_refused_with_a_reason() -> None:
    testbed = build_accounts_testbed()
    client = testbed.build_http_client()
    owner = signed_in(testbed, GEORGIA_MOBILE)
    business = create_business(client, owner)
    path = f"/v1/businesses/{business['id']}"
    opened = client.get(path, headers=owner).json()

    first_tab = client.patch(
        path,
        headers=owner,
        json={"expected_revision": opened["revision"], "city": "Batumi"},
    )
    second_tab = client.patch(
        path,
        headers=owner,
        json={
            "expected_revision": opened["revision"],
            "manager_contacts": [
                {"name": "Nino", "channel": "telegram", "address": "70001"}
            ],
        },
    )

    assert first_tab.status_code == 200, first_tab.text
    assert first_tab.json()["revision"] == opened["revision"] + 1
    assert second_tab.status_code == 409
    body = second_tab.json()
    assert body["error"] == "conflict"
    assert body["reasons"][0]["code"] == "stale_revision"
    assert body["reasons"][0]["details"] == [str(opened["revision"] + 1)]
    current = client.get(path, headers=owner).json()
    assert current["city"] == "Batumi"
    assert current["manager_contacts"] == []
    assert current["revision"] == opened["revision"] + 1
