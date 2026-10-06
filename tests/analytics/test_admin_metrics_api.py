"""
GET /v1/admin/metrics over the real API: the attribution a new owner signs
up with reaches the founder's sources and filters; owners get 403 and bad
filters 422.
"""

from typing import Any

from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE
from tests.setup.launch_steps import (
    NewAssistant,
    accept_dpa,
    add_staff_contact,
    fill_profile,
    go_live,
)

ATTRIBUTION: dict[str, Any] = {
    "utm_source": "Instagram",
    "utm_medium": "story",
    "utm_campaign": "autumn-launch",
    "referrer_host": "l.instagram.com",
    "landing_path": "/",
    "first_seen_at": 1_791_100_000_000_000,
}


def sign_up(
    workshop: Workshop, phone: str, attribution: dict[str, Any] | None
) -> tuple[str, dict[str, Any]]:
    """Sign in with the attribution the cabinet forwards from its cookie."""

    started = workshop.client.post("/v1/auth/otp/start", json={"phone_number": phone})
    assert started.status_code == 200, started.text
    body: dict[str, Any] = {
        "challenge_id": started.json()["challenge_id"],
        "code": str(workshop.otp.codes[-1].code),
    }
    if attribution is not None:
        body["signup_attribution"] = attribution
    verified = workshop.client.post("/v1/auth/otp/verify", json=body)
    assert verified.status_code == 200, verified.text
    session: dict[str, Any] = verified.json()
    return str(session["access_token"]), session


def admin_headers(workshop: Workshop) -> dict[str, str]:
    token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    return bearer(token)


def test_the_sign_up_attribution_reaches_the_founders_sources(
    workshop: Workshop,
) -> None:
    token, session = sign_up(workshop, GEORGIAN_OWNER_PHONE, ATTRIBUTION)
    created = workshop.client.post(
        "/v1/assistants",
        json={"name": "Salobie Bia", "niche_key": "restaurant"},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    assistant = NewAssistant(
        token=token,
        owner_id=str(session["user"]["id"]),
        business_id=str(created.json()["business"]["id"]),
        created=created.json(),
    )
    fill_profile(workshop, assistant)
    add_staff_contact(workshop, assistant)
    accept_dpa(workshop, assistant)
    go_live(workshop, assistant)
    # Signing in again with another cookie keeps the first touch.
    workshop.clock.advance(60)
    sign_up(workshop, GEORGIAN_OWNER_PHONE, {"utm_source": "google"})

    stored = workshop.container.repositories.user_repo().get(session["user"]["id"])
    assert stored is not None and stored.signup_attribution is not None
    assert str(stored.signup_attribution.utm_campaign) == "autumn-launch"

    headers = admin_headers(workshop)
    metrics = workshop.client.get("/v1/admin/metrics", headers=headers)
    assert metrics.status_code == 200, metrics.text
    growth = metrics.json()["growth"]
    assert growth["sources"] == [
        {
            "source": "instagram",
            "referral_code": None,
            "sign_ups": 1,
            "went_live": 1,
            "paying": 0,
        }
    ]
    assert metrics.json()["choices"]["sources"] == ["instagram"]
    owners = {step["step"]: step["owners"] for step in growth["funnel"]}
    assert owners["went_live"] == 1
    assert growth["trials"]["started"] == 1

    other = workshop.client.get(
        "/v1/admin/metrics?source=Google&country=ge&niche=restaurant",
        headers=headers,
    )
    assert other.status_code == 200, other.text
    assert other.json()["growth"]["funnel"][0]["owners"] == 0


def test_owners_may_not_read_the_metrics_and_bad_filters_are_refused(
    workshop: Workshop,
) -> None:
    token, _ = sign_up(workshop, GEORGIAN_OWNER_PHONE, None)
    assert (
        workshop.client.get("/v1/admin/metrics", headers=bearer(token)).status_code
        == 403
    )
    assert workshop.client.get("/v1/admin/metrics").status_code == 401

    headers = admin_headers(workshop)
    for query in (
        "from=2026-02-30",
        "from=yesterday",
        "from=2026-10-05&to=2026-09-01",
        "from=2023-01-01&to=2026-10-01",
        "country=Georgia",
        "niche=bakery",
        "source=%3F%3F",
    ):
        refused = workshop.client.get(f"/v1/admin/metrics?{query}", headers=headers)
        assert refused.status_code == 422, (query, refused.text)

    period = workshop.client.get(
        "/v1/admin/metrics?from=2026-09-01&to=2026-09-30", headers=headers
    )
    assert period.status_code == 200, period.text
    assert (period.json()["period_start"], period.json()["period_end"]) == (
        "2026-09-01",
        "2026-09-30",
    )


def test_an_attribution_with_unknown_fields_is_refused(workshop: Workshop) -> None:
    started = workshop.client.post(
        "/v1/auth/otp/start", json={"phone_number": GEORGIAN_OWNER_PHONE}
    )
    verified = workshop.client.post(
        "/v1/auth/otp/verify",
        json={
            "challenge_id": started.json()["challenge_id"],
            "code": str(workshop.otp.codes[-1].code),
            "signup_attribution": {"gclid": "abc"},
        },
    )

    assert verified.status_code == 422, verified.text


def test_the_founder_includes_platform_admins_on_request(workshop: Workshop) -> None:
    headers = admin_headers(workshop)

    left_out = workshop.client.get("/v1/admin/metrics", headers=headers)
    included = workshop.client.get(
        "/v1/admin/metrics", params={"include_admins": "true"}, headers=headers
    )
    broken = workshop.client.get(
        "/v1/admin/metrics", params={"include_admins": "maybe"}, headers=headers
    )

    assert left_out.status_code == 200, left_out.text
    assert left_out.json()["growth"]["are_platform_admins_included"] is False
    assert included.status_code == 200, included.text
    assert included.json()["growth"]["are_platform_admins_included"] is True
    assert included.json()["growth"]["excluded_platform_admins"] == 0
    assert broken.status_code == 422
