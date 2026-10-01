from typing import Any

from app.schemas.typings.contacts.prefixed_id import ContactId
from tests.compliance.visitor_records import seed_visitor
from tests.users.accounts_testbed import (
    GEORGIA_MOBILE,
    GERMANY_MOBILE,
    bearer,
    build_accounts_testbed,
)


def test_dpa_audit_log_export_and_erasure_over_http() -> None:
    testbed = build_accounts_testbed()
    client = testbed.build_http_client()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    headers = bearer(owner.access_token)
    business = testbed.create_restaurant(owner.user.id)
    visitor = seed_visitor(testbed, business, "Giorgi", "+995577123456", "42", "ka")
    base_url = f"/v1/businesses/{business.id}"

    status_before = client.get(f"{base_url}/dpa", headers=headers)
    accepted = client.post(f"{base_url}/dpa", headers=headers)
    assert status_before.status_code == 200
    assert status_before.json()["is_current_version_accepted"] is False
    assert accepted.status_code == 201
    assert accepted.json()["is_current_version_accepted"] is True
    assert accepted.json()["latest_acceptance"]["accepted_by"] == str(owner.user.id)

    exported = client.get(
        f"{base_url}/contacts/{visitor.contact.id}/export",
        headers=headers,
    )
    assert exported.status_code == 200
    export: dict[str, Any] = exported.json()
    assert export["records"]["contact"]["name"] == "Giorgi"
    assert export["records"]["contact"]["phone_number"] == "+995577123456"
    assert len(export["records"]["messages"]) == 3
    assert len(export["records"]["calls"]) == 2

    erased = client.delete(f"{base_url}/contacts/{visitor.contact.id}", headers=headers)
    assert erased.status_code == 200
    assert erased.json()["deleted_messages"] == 3
    assert erased.json()["deleted_recordings"] == 2

    audit_log = client.get(f"{base_url}/audit-log", headers=headers)
    limited = client.get(f"{base_url}/audit-log?limit=1", headers=headers)
    assert audit_log.status_code == 200
    assert [entry["action"] for entry in audit_log.json()] == [
        "delete",
        "export",
        "create",
    ]
    assert audit_log.json()[0]["ip_address"] == "testclient"
    assert [entry["action"] for entry in limited.json()] == ["delete"]

    gone = client.get(
        f"{base_url}/contacts/{visitor.contact.id}/export", headers=headers
    )
    assert gone.status_code == 404


def test_compliance_routes_report_errors_with_status_codes() -> None:
    testbed = build_accounts_testbed()
    client = testbed.build_http_client()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    stranger = testbed.sign_in_with_phone(GERMANY_MOBILE)
    owner_headers = bearer(owner.access_token)
    business = testbed.create_restaurant(owner.user.id)
    base_url = f"/v1/businesses/{business.id}"

    responses = {
        "no token": client.get(f"{base_url}/dpa"),
        "stranger": client.post(
            f"{base_url}/dpa", headers=bearer(stranger.access_token)
        ),
        "malformed business": client.get("/v1/businesses/x/dpa", headers=owner_headers),
        "limit not a number": client.get(
            f"{base_url}/audit-log?limit=many",
            headers=owner_headers,
        ),
        "limit too small": client.get(
            f"{base_url}/audit-log?limit=0",
            headers=owner_headers,
        ),
        "limit too large": client.get(
            f"{base_url}/audit-log?limit=1001",
            headers=owner_headers,
        ),
        "malformed contact": client.get(
            f"{base_url}/contacts/someone/export",
            headers=owner_headers,
        ),
        "unknown contact": client.delete(
            f"{base_url}/contacts/{ContactId()}",
            headers=owner_headers,
        ),
    }

    assert {name: response.status_code for name, response in responses.items()} == {
        "no token": 401,
        "stranger": 404,
        "malformed business": 404,
        "limit not a number": 422,
        "limit too small": 422,
        "limit too large": 422,
        "malformed contact": 404,
        "unknown contact": 404,
    }
