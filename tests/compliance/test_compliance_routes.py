from typing import Any

from app.schemas.typings.contacts.prefixed_id import ContactId
from tests.compliance.visitor_records import seed_visitor
from tests.users.accounts_phones import GEORGIA_MOBILE, GERMANY_MOBILE
from tests.users.accounts_testbed import bearer, build_accounts_testbed


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
    next_page = client.get(
        f"{base_url}/audit-log",
        headers=headers,
        params={"limit": "1", "cursor": limited.json()["next_cursor"]},
    )
    filtered = client.get(
        f"{base_url}/audit-log",
        headers=headers,
        params={"action": "export", "entity": "contact", "actor_id": owner.user.id},
    )
    assert audit_log.status_code == 200
    assert [entry["action"] for entry in audit_log.json()["items"]] == [
        "delete",
        "export",
        "create",
    ]
    assert audit_log.json()["items"][0]["ip_address"] == "testclient"
    assert audit_log.json()["next_cursor"] is None
    assert audit_log.json()["entities"] == ["contact", "dpa_acceptance"]
    assert [entry["action"] for entry in limited.json()["items"]] == ["delete"]
    assert [entry["action"] for entry in next_page.json()["items"]] == ["export"]
    assert [entry["action"] for entry in filtered.json()["items"]] == ["export"]

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
            f"{base_url}/audit-log?limit=201",
            headers=owner_headers,
        ),
        "broken cursor": client.get(
            f"{base_url}/audit-log?cursor=bm90LWEtY3Vyc29y",
            headers=owner_headers,
        ),
        "unknown action": client.get(
            f"{base_url}/audit-log?action=steal",
            headers=owner_headers,
        ),
        "malformed actor": client.get(
            f"{base_url}/audit-log?actor_id=someone",
            headers=owner_headers,
        ),
        "since not a moment": client.get(
            f"{base_url}/audit-log?since=yesterday",
            headers=owner_headers,
        ),
        "negative until": client.get(
            f"{base_url}/audit-log?until=-5",
            headers=owner_headers,
        ),
        "contacts limit": client.get(
            f"{base_url}/contacts?limit=0",
            headers=owner_headers,
        ),
        "contacts of a stranger": client.get(
            f"{base_url}/contacts",
            headers=bearer(stranger.access_token),
        ),
        "unknown contact page": client.get(
            f"{base_url}/contacts/{ContactId()}",
            headers=owner_headers,
        ),
        "unknown agreement version": client.get("/v1/legal/dpa/1999-01-01"),
        "malformed agreement version": client.get("/v1/legal/dpa/%20bad"),
        "unknown agreement language": client.get(
            "/v1/legal/dpa/2026-10-01?language=not a language"
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
        "broken cursor": 422,
        "unknown action": 422,
        "malformed actor": 422,
        "since not a moment": 422,
        "negative until": 422,
        "contacts limit": 422,
        "contacts of a stranger": 404,
        "unknown contact page": 404,
        "unknown agreement version": 404,
        "malformed agreement version": 404,
        "unknown agreement language": 422,
        "malformed contact": 404,
        "unknown contact": 404,
    }


def test_customers_and_the_agreement_text_over_http() -> None:
    testbed = build_accounts_testbed()
    client = testbed.build_http_client()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    headers = bearer(owner.access_token)
    business = testbed.create_restaurant(owner.user.id)
    giorgi = seed_visitor(testbed, business, "Giorgi", "+995577123456", "42", "ka")
    testbed.clock.advance(5)
    seed_visitor(testbed, business, "Nino", "+995577654321", "43", "ru")
    base_url = f"/v1/businesses/{business.id}"

    first = client.get(f"{base_url}/contacts?limit=1", headers=headers)
    second = client.get(
        f"{base_url}/contacts",
        headers=headers,
        params={"limit": "1", "cursor": first.json()["next_cursor"]},
    )
    found = client.get(f"{base_url}/contacts?search=123 456", headers=headers)
    detail = client.get(f"{base_url}/contacts/{giorgi.contact.id}", headers=headers)
    status = client.get(f"{base_url}/dpa", headers=headers)
    document = client.get(status.json()["document_url"], params={"language": "ka"})

    assert [item["name"] for item in first.json()["items"]] == ["Nino"]
    assert [item["name"] for item in second.json()["items"]] == ["Giorgi"]
    assert second.json()["next_cursor"] is None
    assert [item["name"] for item in found.json()["items"]] == ["Giorgi"]
    assert detail.status_code == 200
    assert detail.json()["contact"]["conversation_count"] == 2
    assert sorted(item["channel"] for item in detail.json()["conversations"]) == [
        "phone",
        "telegram",
    ]
    assert status.json()["document_url"] == "/v1/legal/dpa/2026-10-01"
    assert document.status_code == 200
    assert document.json()["language"] == "ka"
    assert document.json()["text"].startswith("# ")
