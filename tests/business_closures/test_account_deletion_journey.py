"""
DELETE /v1/me: a person deletes their own account. Staff leave the
business and their sign-in records go; the last owner of a business that
is not closing is refused, until it closes; the platform team is refused.
"""

from tests.business_closures.closure_world import (
    DEMO_STAFF_PHONE,
    ClosureWorld,
    open_closure_world,
)
from tests.e2e.harness import bearer
from tests.e2e.harness_settings import ADMIN_EMAIL

NEW_OWNER_PHONE: str = "+995 555 77 77 01"


def members_of(world: ClosureWorld) -> list[str]:
    team = world.workshop.client.get(
        f"/v1/businesses/{world.business_b}", headers=world.owner_b
    )
    assert team.status_code == 200, team.text
    return [str(member["user_id"]) for member in team.json()["members"]]


def test_a_staff_member_deletes_the_account_and_leaves_the_business() -> None:
    with open_closure_world() as world:
        client = world.workshop.client
        me = client.get("/v1/me", headers=world.staff_b).json()
        assert str(me["user"]["id"]) in members_of(world)

        deleted = client.delete("/v1/me", headers=world.staff_b)

        assert deleted.status_code == 204, deleted.text
        assert client.get("/v1/me", headers=world.staff_b).status_code == 401
        assert str(me["user"]["id"]) not in members_of(world)
        # Signing in again with the same number starts a new, empty account.
        world.workshop.clock.advance(60)
        token, session = world.workshop.sign_in_with_phone(DEMO_STAFF_PHONE)
        assert session["user"]["id"] != me["user"]["id"]
        assert client.get("/v1/businesses", headers=bearer(token)).json() == []


def test_the_last_owner_of_an_open_business_is_refused() -> None:
    with open_closure_world() as world:
        refused = world.workshop.client.delete("/v1/me", headers=world.owner_a)

        assert refused.status_code == 409
        assert "Salobie" in refused.json()["message"]
        assert refused.json()["reasons"] == [
            {
                "code": "last_business_owner",
                "message": refused.json()["message"],
                "details": [world.business_a],
            }
        ]
        assert (
            world.workshop.client.get("/v1/me", headers=world.owner_a).status_code
            == 200
        )


def test_closing_the_business_first_lets_its_owner_go() -> None:
    with open_closure_world() as world:
        client = world.workshop.client
        owner = bearer(world.workshop.sign_in_with_phone(NEW_OWNER_PHONE)[0])
        created = client.post(
            "/v1/businesses",
            json={"name": "Lavka", "niche_key": "restaurant"},
            headers=owner,
        )
        business_id = str(created.json()["id"])
        closed = client.post(
            f"/v1/businesses/{business_id}/closure",
            json={"confirmation_name": "lavka "},
            headers=owner,
        )
        assert closed.status_code == 200, closed.text

        deleted = client.delete("/v1/me", headers=owner)

        assert deleted.status_code == 204, deleted.text
        assert world.rows_of(business_id)["business_closures"] == 1


def test_a_member_of_the_platform_team_is_refused() -> None:
    with open_closure_world() as world:
        admin = bearer(world.workshop.sign_in_with_email(ADMIN_EMAIL)[0])

        refused = world.workshop.client.delete("/v1/me", headers=admin)

        assert refused.status_code == 409
        assert "platform team" in refused.json()["message"]
        assert [reason["code"] for reason in refused.json()["reasons"]] == [
            "platform_team"
        ]
