"""End to end over HTTP: a second owner is isolated from the first business,
and platform admin access to it is audited.
"""

from app.schemas.constants.localization import OtpDeliveryChannel
from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import JsonObject, sign_in_and_create_restaurant


def test_second_owner_in_italy_is_isolated_and_admin_access_is_audited(
    workshop: Workshop,
) -> None:
    client = workshop.client
    georgian_token, _, georgian_business_id = sign_in_and_create_restaurant(workshop)
    georgian_base = f"/v1/businesses/{georgian_business_id}"

    # An owner signing in by e-mail opens a business in Italy.
    italian_token, italian_session = workshop.sign_in_with_email(
        "Giulia@Trattoria.example"
    )
    assert italian_session["user"]["email"] == "giulia@trattoria.example"
    assert workshop.otp.codes[-1].channel is OtpDeliveryChannel.EMAIL
    italian_headers = bearer(italian_token)
    created = client.post(
        "/v1/businesses",
        json={
            "name": "Trattoria Giulia",
            "niche_key": "restaurant",
            "country_code": "IT",
        },
        headers=italian_headers,
    )
    assert created.status_code == 201, created.text
    italian: JsonObject = created.json()
    assert (italian["currency_code"], italian["timezone"]) == ("EUR", "Europe/Rome")
    assert italian["languages"][0] == "it"

    # Neither owner sees the other's business, by any id.
    assert client.get(georgian_base, headers=italian_headers).status_code == 404
    for section in ("bookings", "conversations", "knowledge", "profile", "billing"):
        response = client.get(f"{georgian_base}/{section}", headers=italian_headers)
        assert response.status_code == 404, section
    assert (
        client.get(
            f"/v1/businesses/{italian['id']}", headers=bearer(georgian_token)
        ).status_code
        == 404
    )
    listed = client.get("/v1/businesses", headers=italian_headers).json()
    assert [item["name"] for item in listed] == ["Trattoria Giulia"]
    assert client.get("/v1/admin/clients", headers=italian_headers).status_code == 403

    # The platform admin sees every client; entering a cabinet is audited.
    admin_token, admin_session = workshop.sign_in_with_email(ADMIN_EMAIL)
    admin_headers = bearer(admin_token)
    assert admin_session["user"]["is_platform_admin"] is True
    clients = client.get("/v1/admin/clients", headers=admin_headers).json()
    assert clients["totals"]["client_count"] == 2
    # Support looks in only after "Open cabinet" with a reason: an hour,
    # read-only.
    before = client.get(f"{georgian_base}/bookings", headers=admin_headers)
    assert before.status_code == 403
    assert before.json()["reasons"][0]["code"] == "support_access_required"
    opened = client.post(
        f"/v1/admin/clients/{georgian_business_id}/open",
        headers=admin_headers,
        json={"reason": "Owner asked why a booking is missing"},
    )
    assert opened.status_code == 200, opened.text
    assert "bookings" in opened.json()["sections"]
    admin_view = client.get(f"{georgian_base}/bookings", headers=admin_headers)
    assert admin_view.status_code == 200
    change = client.patch(georgian_base, headers=admin_headers, json={})
    assert change.status_code == 403
    assert change.json()["reasons"][0]["code"] == "support_read_only"
    banner = client.get(
        f"{georgian_base}/support-access", headers=bearer(georgian_token)
    ).json()
    assert [session["reason"] for session in banner["sessions"]] == [
        "Owner asked why a booking is missing"
    ]

    audit = client.get(
        f"{georgian_base}/audit-log", headers=bearer(georgian_token)
    ).json()
    admin_entries = [
        (entry["action"], entry["entity"])
        for entry in audit["items"]
        if entry["actor_id"] == admin_session["user"]["id"]
    ]
    # Newest first: support's look at the bookings, then the look itself.
    assert admin_entries == [
        ("view", "booking"),
        ("support_access_start", "support_access"),
    ]
