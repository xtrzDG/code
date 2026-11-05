from typing import Any

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.localization import OtpDeliveryChannel
from tests.users.accounts_phones import (
    GEORGIA_MOBILE,
    ISRAEL_MOBILE,
    NORTH_KOREA_MOBILE,
)
from tests.users.accounts_testbed import build_accounts_testbed


def test_full_sign_in_profile_and_logout_over_http() -> None:
    testbed = build_accounts_testbed()
    client = testbed.build_http_client()

    start_response = client.post(
        "/v1/auth/otp/start",
        json={
            "phone_number": "555 12 34 56",
            "country_hint": "GE",
            "preferred_delivery_channel": "whatsapp",
        },
    )
    assert start_response.status_code == 200
    challenge: dict[str, Any] = start_response.json()
    assert challenge["delivery_channel"] == "whatsapp"
    assert challenge["phone_number"] == "+995555123456"
    assert challenge["masked_destination"] == "+995 *** ** ** 56"
    assert challenge["locale"] == "ka"
    assert "code" not in challenge

    verify_response = client.post(
        "/v1/auth/otp/verify",
        json={
            "challenge_id": challenge["challenge_id"],
            "code": testbed.otp_delivery.last_code(),
        },
    )
    assert verify_response.status_code == 200
    login: dict[str, Any] = verify_response.json()
    assert login["is_new_user"] is True
    assert login["user"]["country_code"] == "GE"
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    me_response = client.get("/v1/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["user"]["id"] == login["user"]["id"]
    assert me_response.json()["memberships"] == []

    patch_response = client.patch(
        "/v1/me",
        headers=headers,
        json={"display_name": "נועה", "locale": "he"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["display_name"] == "נועה"
    assert patch_response.json()["locale"] == "he"

    logout_response = client.post("/v1/auth/logout", headers=headers)
    assert logout_response.status_code == 204
    assert logout_response.content == b""

    after_logout = client.get("/v1/me", headers=headers)
    assert after_logout.status_code == 401
    assert after_logout.headers["WWW-Authenticate"] == "Bearer"


def test_login_audit_records_the_client_address() -> None:
    testbed = build_accounts_testbed()
    client = testbed.build_http_client()
    challenge = client.post(
        "/v1/auth/otp/start",
        json={"email": "Owner@Example.com"},
    ).json()

    client.post(
        "/v1/auth/otp/verify",
        json={
            "challenge_id": challenge["challenge_id"],
            "code": testbed.otp_delivery.last_code(),
        },
    )

    login_entries = [
        entry
        for entry in testbed.audit_log_collection.list_all()
        if entry.action is AuditAction.LOGIN
    ]
    assert [entry.ip_address for entry in login_entries] == ["testclient"]


def test_invalid_bodies_are_reported_as_validation_errors() -> None:
    client = build_accounts_testbed().build_http_client()

    bad_enum = client.post(
        "/v1/auth/otp/start",
        json={"phone_number": GEORGIA_MOBILE, "preferred_delivery_channel": "fax"},
    )
    bad_json = client.post(
        "/v1/auth/otp/start",
        content=b"{not json",
        headers={"Content-Type": "application/json"},
    )
    unknown_field = client.post(
        "/v1/auth/otp/start",
        json={"phone_number": GEORGIA_MOBILE, "role": "platform_admin"},
    )
    short_code = client.post(
        "/v1/auth/otp/verify",
        json={"challenge_id": "otp_challenge_nope", "code": "12"},
    )

    for response in (bad_enum, bad_json, unknown_field, short_code):
        assert response.status_code == 422
        assert response.json()["error"] == "validation_failed"

    assert "preferred_delivery_channel" in bad_enum.json()["message"]
    assert "fax" not in bad_enum.json()["message"]


def test_wrong_code_throttling_and_restricted_country_status_codes() -> None:
    testbed = build_accounts_testbed()
    client = testbed.build_http_client()
    challenge = client.post(
        "/v1/auth/otp/start",
        json={"phone_number": ISRAEL_MOBILE},
    ).json()
    correct_code = testbed.otp_delivery.last_code()

    wrong_code = client.post(
        "/v1/auth/otp/verify",
        json={
            "challenge_id": challenge["challenge_id"],
            "code": "000000" if correct_code != "000000" else "111111",
        },
    )
    repeated_start = client.post(
        "/v1/auth/otp/start",
        json={"phone_number": ISRAEL_MOBILE},
    )
    restricted = client.post(
        "/v1/auth/otp/start",
        json={"phone_number": NORTH_KOREA_MOBILE},
    )
    invalid_phone = client.post(
        "/v1/auth/otp/start",
        json={"phone_number": "12"},
    )

    assert wrong_code.status_code == 401
    assert repeated_start.status_code == 429
    assert restricted.status_code == 403
    assert invalid_phone.status_code == 422


def test_profile_routes_require_a_bearer_token() -> None:
    client = build_accounts_testbed().build_http_client()

    missing = client.get("/v1/me")
    wrong_scheme = client.get("/v1/me", headers={"Authorization": "Basic abc"})
    unknown_token = client.patch(
        "/v1/me",
        headers={"Authorization": "Bearer unknown"},
        json={"locale": "en"},
    )
    logout_without_token = client.post("/v1/auth/logout")

    for response in (missing, wrong_scheme, unknown_token, logout_without_token):
        assert response.status_code == 401


def test_openapi_documents_bodies_read_by_the_strict_parser() -> None:
    client = build_accounts_testbed().build_http_client()

    schema: dict[str, Any] = client.get("/openapi.json").json()

    paths: dict[str, Any] = schema["paths"]
    start_body = paths["/v1/auth/otp/start"]["post"]["requestBody"]
    start_schema = start_body["content"]["application/json"]["schema"]
    assert start_body["required"] is True
    assert set(start_schema["properties"]) == {
        "phone_number",
        "email",
        "country_hint",
        "locale",
        "preferred_delivery_channel",
        "turnstile_token",
    }
    settings_body = paths["/v1/businesses/{business_id}"]["patch"]["requestBody"]
    settings_schema = settings_body["content"]["application/json"]["schema"]
    contacts_schema = settings_schema["properties"]["manager_contacts"]["anyOf"][0]
    assert "$ref" not in str(settings_schema)
    assert set(contacts_schema["items"]["properties"]) == {
        "name",
        "channel",
        "address",
        "language",
        "preferences",
    }
    assert "requestBody" in paths["/v1/me"]["patch"]
    assert "requestBody" in paths["/v1/businesses/{business_id}/members"]["post"]
    assert "requestBody" in paths["/v1/businesses"]["post"]


def test_code_requests_over_the_address_limit_are_refused_over_http() -> None:
    testbed = build_accounts_testbed({"OTP_SENDS_PER_IP_PER_HOUR": "1"})
    client = testbed.build_http_client()

    first = client.post("/v1/auth/otp/start", json={"phone_number": GEORGIA_MOBILE})
    second = client.post(
        "/v1/auth/otp/start",
        # The address comes from the connection, never from the body.
        json={"phone_number": "+995 555 12 34 99", "client_ip_address": "1.2.3.4"},
    )
    third = client.post(
        "/v1/auth/otp/start", json={"phone_number": "+995 555 12 34 99"}
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 422
    assert third.status_code == 429
    assert third.json()["error"] == "rate_limited"


def test_failed_code_delivery_hides_provider_details_over_http() -> None:
    testbed = build_accounts_testbed()
    testbed.otp_delivery.failing_channels = set(OtpDeliveryChannel)

    response = testbed.build_http_client().post(
        "/v1/auth/otp/start",
        json={"phone_number": "555 12 34 56", "country_hint": "GE"},
    )

    assert response.status_code == 502
    assert response.json()["error"] == "external_service_error"
    assert "could not send a login code" in response.json()["message"]
    assert "provider is down" not in response.json()["message"]
