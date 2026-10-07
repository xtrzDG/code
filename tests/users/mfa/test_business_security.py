"""
A business may require two-factor sign-in of its whole team: the owner
turns it on from a two-factor session; members signed in with one factor
are refused (403, reason `mfa_required`) until they set up an
authenticator in Account → Security.
"""

from tests.e2e.harness import Workshop, bearer
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE, sign_in_and_create_restaurant
from tests.users.mfa.mfa_api import reason_codes, set_up_authenticator

STAFF_PHONE: str = "+995 555 77 88 99"


def test_the_owner_requires_two_factor_sign_in_of_the_team(
    workshop: Workshop,
) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    owner = bearer(token)
    base: str = f"/v1/businesses/{business_id}"
    invited = workshop.client.post(
        f"{base}/members",
        json={"phone_number": STAFF_PHONE, "role": "staff"},
        headers=owner,
    )
    staff_token, _ = workshop.sign_in_with_phone(STAFF_PHONE)
    staff = bearer(staff_token)

    one_factor = workshop.client.put(
        f"{base}/security", json={"require_mfa_for_members": True}, headers=owner
    )
    set_up_authenticator(workshop, token, GEORGIAN_OWNER_PHONE)
    turned_on = workshop.client.put(
        f"{base}/security", json={"require_mfa_for_members": True}, headers=owner
    )
    staff_refused = workshop.client.get(base, headers=staff)
    staff_changes = workshop.client.put(
        f"{base}/security", json={"require_mfa_for_members": False}, headers=staff
    )
    set_up_authenticator(workshop, staff_token, STAFF_PHONE)
    staff_allowed = workshop.client.get(base, headers=staff)
    seen_by_owner = workshop.client.get(f"{base}/security", headers=owner)

    assert invited.status_code == 201, invited.text
    assert one_factor.status_code == 403
    assert reason_codes(one_factor) == ["mfa_required"]
    assert turned_on.status_code == 200, turned_on.text
    assert turned_on.json() == {
        "business_id": business_id,
        "require_mfa_for_members": True,
        "members_without_two_factor": 1,
        "viewer_auth_level": "two_factor",
    }
    assert staff_refused.status_code == 403
    assert reason_codes(staff_refused) == ["mfa_required"]
    assert staff_changes.status_code == 403
    assert staff_allowed.status_code == 200, staff_allowed.text
    assert seen_by_owner.json()["members_without_two_factor"] == 0


def test_turning_the_requirement_off_needs_no_authenticator(
    workshop: Workshop,
) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    base: str = f"/v1/businesses/{business_id}"

    turned_off = workshop.client.put(
        f"{base}/security",
        json={"require_mfa_for_members": False},
        headers=bearer(token),
    )
    audit = workshop.client.get(f"{base}/audit-log", headers=bearer(token)).json()

    assert turned_off.status_code == 200, turned_off.text
    assert turned_off.json()["require_mfa_for_members"] is False
    assert turned_off.json()["viewer_auth_level"] == "one_factor"
    assert ("business_security", "update") in {
        (entry["entity"], entry["action"]) for entry in audit["items"]
    }
