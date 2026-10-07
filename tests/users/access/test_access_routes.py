"""
The access endpoints over the real API: the person's signed-in devices
(list, end one, end the others), the platform admin team, and the owner's
side of support access (consent to changes, ending access) next to the
admin leaving the cabinet.
"""

from typing import Any

from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE, sign_in_and_create_restaurant
from tests.users.mfa.mfa_api import RESEND_WAIT_SECONDS, reason_codes

SESSIONS_URL: str = "/v1/me/sessions"
TEAM_URL: str = "/v1/admin/team"
PHONE_BROWSER: str = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)


def sign_in_again(workshop: Workshop, user_agent: str | None = None) -> str:
    workshop.clock.advance(RESEND_WAIT_SECONDS)
    headers = {} if user_agent is None else {"User-Agent": user_agent}
    started = workshop.client.post(
        "/v1/auth/otp/start", json={"phone_number": GEORGIAN_OWNER_PHONE}
    )
    assert started.status_code == 200, started.text
    verified = workshop.client.post(
        "/v1/auth/otp/verify",
        json={
            "challenge_id": started.json()["challenge_id"],
            "code": str(workshop.otp.codes[-1].code),
        },
        headers=headers,
    )
    assert verified.status_code == 200, verified.text
    return str(verified.json()["access_token"])


def sessions_of(workshop: Workshop, token: str) -> list[dict[str, Any]]:
    listed = workshop.client.get(SESSIONS_URL, headers=bearer(token))
    assert listed.status_code == 200, listed.text
    items: list[dict[str, Any]] = listed.json()["items"]
    return items


def test_a_person_sees_and_ends_their_devices(workshop: Workshop) -> None:
    laptop, _ = workshop.sign_in_with_phone(GEORGIAN_OWNER_PHONE)
    phone = sign_in_again(workshop, PHONE_BROWSER)

    items = sessions_of(workshop, laptop)
    [current] = [item for item in items if item["is_current"]]
    [other] = [item for item in items if not item["is_current"]]
    ended = workshop.client.delete(
        f"{SESSIONS_URL}/{other['id']}", headers=bearer(laptop)
    )
    again = workshop.client.delete(
        f"{SESSIONS_URL}/{other['id']}", headers=bearer(laptop)
    )

    assert len(items) == 2
    assert other["device"]["kind"] == "phone"
    assert other["device"]["operating_system"] == "iOS"
    assert current["last_seen_at"] >= current["created_at"]
    assert ended.status_code == 204
    assert again.status_code == 404
    assert workshop.client.get(SESSIONS_URL, headers=bearer(phone)).status_code == 401


def test_signing_out_everywhere_else_keeps_this_device(workshop: Workshop) -> None:
    laptop, _ = workshop.sign_in_with_phone(GEORGIAN_OWNER_PHONE)
    others = [sign_in_again(workshop), sign_in_again(workshop, PHONE_BROWSER)]

    revoked = workshop.client.post(
        f"{SESSIONS_URL}/revoke-others", headers=bearer(laptop)
    )

    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["revoked_count"] == 2
    for token in others:
        assert (
            workshop.client.get(SESSIONS_URL, headers=bearer(token)).status_code == 401
        )
    assert [item["is_current"] for item in sessions_of(workshop, laptop)] == [True]


def test_the_admin_team_over_the_api(workshop: Workshop) -> None:
    admin, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    owner, _ = workshop.sign_in_with_phone(GEORGIAN_OWNER_PHONE)
    headers = bearer(admin)

    first = workshop.client.get(TEAM_URL, headers=headers)
    added = workshop.client.post(
        TEAM_URL,
        json={"email": "billing@workshop.example", "role": "billing"},
        headers=headers,
    )
    newcomer = added.json()["items"][1]
    changed = workshop.client.patch(
        f"{TEAM_URL}/{newcomer['id']}",
        json={"role": "support_readonly"},
        headers=headers,
    )
    removed = workshop.client.delete(f"{TEAM_URL}/{newcomer['id']}", headers=headers)
    last_super = workshop.client.delete(
        f"{TEAM_URL}/{first.json()['items'][0]['id']}", headers=headers
    )

    assert first.status_code == 200, first.text
    [me] = first.json()["items"]
    assert (me["role"], me["is_you"], me["email"]) == ("super", True, ADMIN_EMAIL)
    assert added.status_code == 200, added.text
    assert newcomer["role"] == "billing"
    assert changed.json()["items"][1]["role"] == "support_readonly"
    assert removed.status_code == 204
    assert last_super.status_code == 409
    assert workshop.client.get(TEAM_URL, headers=bearer(owner)).status_code == 403
    assert (
        workshop.client.get("/v1/me", headers=headers).json()["platform_admin_role"]
        == "super"
    )


def test_the_owner_decides_and_ends_support_access(workshop: Workshop) -> None:
    owner, _, business_id = sign_in_and_create_restaurant(workshop)
    admin, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    base = f"/v1/businesses/{business_id}"
    opened = workshop.client.post(
        f"/v1/admin/clients/{business_id}/open",
        json={"reason": "Help with the opening hours"},
        headers=bearer(admin),
    )
    no_reason = workshop.client.post(
        f"/v1/admin/clients/{business_id}/open", json={}, headers=bearer(admin)
    )

    before = workshop.client.patch(f"{base}/profile", json={}, headers=bearer(admin))
    allowed = workshop.client.put(
        f"{base}/support-access/write-access",
        json={"is_allowed": True, "hours": 2},
        headers=bearer(owner),
    )
    by_support = workshop.client.put(
        f"{base}/support-access/write-access",
        json={"is_allowed": True},
        headers=bearer(admin),
    )
    change = workshop.client.patch(f"{base}/profile", json={}, headers=bearer(admin))
    owner_only = workshop.client.patch(base, json={}, headers=bearer(admin))
    ended = workshop.client.delete(f"{base}/support-access", headers=bearer(owner))
    after = workshop.client.get(f"{base}/bookings", headers=bearer(admin))

    assert opened.status_code == 200, opened.text
    assert opened.json()["can_write"] is False
    assert no_reason.status_code == 422
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["write_access"]["is_allowed"] is True
    assert by_support.status_code == 403
    assert reason_codes(before) == ["support_read_only"]
    assert change.status_code == 200, change.text
    assert owner_only.status_code == 403
    assert ended.status_code == 204
    assert after.status_code == 403
    assert reason_codes(after) == ["support_access_required"]


def test_the_admin_leaves_the_cabinet(workshop: Workshop) -> None:
    owner, _, business_id = sign_in_and_create_restaurant(workshop)
    admin, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    workshop.client.post(
        f"/v1/admin/clients/{business_id}/open",
        json={"reason": "Help with the opening hours"},
        headers=bearer(admin),
    )
    seen = workshop.client.get(
        f"/v1/businesses/{business_id}/support-access", headers=bearer(admin)
    )

    left = workshop.client.delete(
        f"/v1/admin/clients/{business_id}/access", headers=bearer(admin)
    )
    banner = workshop.client.get(
        f"/v1/businesses/{business_id}/support-access", headers=bearer(owner)
    )

    assert seen.json()["is_support_viewer"] is True
    assert left.status_code == 204
    assert banner.json()["sessions"] == []
