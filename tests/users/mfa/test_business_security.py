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
    owner = bearer(set_up_authenticator(workshop, token, GEORGIAN_OWNER_PHONE)[0])
    turned_on = workshop.client.put(
        f"{base}/security", json={"require_mfa_for_members": True}, headers=owner
    )
    staff_refused = workshop.client.get(base, headers=staff)
    staff_changes = workshop.client.put(
        f"{base}/security", json={"require_mfa_for_members": False}, headers=staff
    )
    staff = bearer(set_up_authenticator(workshop, staff_token, STAFF_PHONE)[0])
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
        "staff_may_play_recordings": False,
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


def test_the_owner_lets_staff_play_call_recordings(workshop: Workshop) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    owner = bearer(token)
    base: str = f"/v1/businesses/{business_id}"
    workshop.client.post(
        f"{base}/members",
        json={"phone_number": STAFF_PHONE, "role": "staff"},
        headers=owner,
    )
    staff = bearer(workshop.sign_in_with_phone(STAFF_PHONE)[0])

    by_default = workshop.client.get(f"{base}/security", headers=staff)
    staff_tries = workshop.client.put(
        f"{base}/security", json={"staff_may_play_recordings": True}, headers=staff
    )
    # One factor is enough: only the two-factor requirement needs two.
    allowed = workshop.client.put(
        f"{base}/security", json={"staff_may_play_recordings": True}, headers=owner
    )
    seen_by_staff = workshop.client.get(f"{base}/security", headers=staff)
    taken_back = workshop.client.put(
        f"{base}/security", json={"staff_may_play_recordings": False}, headers=owner
    )
    audit = workshop.client.get(f"{base}/audit-log", headers=owner).json()

    assert by_default.json()["staff_may_play_recordings"] is False
    assert staff_tries.status_code == 403
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["staff_may_play_recordings"] is True
    # Left out of the request, the two-factor requirement stays as it was.
    assert allowed.json()["require_mfa_for_members"] is False
    assert seen_by_staff.json()["staff_may_play_recordings"] is True
    assert taken_back.json()["staff_may_play_recordings"] is False
    updates = [
        entry
        for entry in audit["items"]
        if (entry["entity"], entry["action"]) == ("business_security", "update")
    ]
    assert len(updates) == 2
