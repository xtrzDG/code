"""
Removing a member ends everything they hold in the business at once: their
cabinet session is refused on the business's routes (membership is read
at every request), and the API keys they made are revoked with them, each
audited, with the webhooks those keys subscribed. Keys other people made
keep working.
"""

from app.schemas.constants.compliance import AuditAction
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.e2e.harness import bearer
from tests.integrations.integration_shop import IntegrationShop, open_integration_shop

CO_OWNER_PHONE: str = "+995 555 44 33 22"


def co_owner_token(shop: IntegrationShop) -> tuple[str, str]:
    """A second owner invited by the first, signed in: (token, user id)."""

    invited = shop.post(
        f"{shop.base}/members", {"phone_number": CO_OWNER_PHONE, "role": "owner"}
    )
    assert invited.status_code == 201, invited.text
    token, session = shop.workshop.sign_in_with_phone(CO_OWNER_PHONE)
    return token, str(session["user"]["id"])


def key_as(shop: IntegrationShop, token: str, name: str) -> str:
    created = shop.client.post(
        f"{shop.base}/api-keys",
        json={"name": name, "scopes": ["leads:read", "webhooks:manage"]},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    return str(created.json()["token"])


def key_deletions(shop: IntegrationShop) -> list[tuple[str, str]]:
    business_id = BusinessId(shop.business_id)
    container = shop.workshop.container
    with container.utilities.storage_scope().scoped_to_business(business_id):
        entries = container.repositories.audit_log_repo().list_by_business(business_id)
    return [
        (str(entry.actor_id), str(entry.entity_id))
        for entry in entries
        if entry.action is AuditAction.DELETE and str(entry.entity) == "api_key"
    ]


def test_a_removed_member_takes_their_keys_and_loses_the_business() -> None:
    with open_integration_shop() as shop:
        token, member_id = co_owner_token(shop)
        theirs = key_as(shop, token, "Their Zapier")
        ours = shop.add_api_key(name="Our CRM")
        hooked = shop.api(
            "POST",
            "/webhooks",
            theirs,
            {"url": "https://hooks.zapier.com/1", "event_types": ["lead.created"]},
        )
        before = shop.client.get(shop.base, headers=bearer(token))

        removed = shop.delete(f"{shop.base}/members/{member_id}")
        their_key = shop.api("GET", "/me", theirs)
        our_key = shop.api("GET", "/me", ours)
        their_session = shop.client.get(shop.base, headers=bearer(token))
        their_bookings = shop.client.get(f"{shop.base}/bookings", headers=bearer(token))
        keys = {
            item["name"]: item
            for item in shop.get(f"{shop.base}/api-keys").json()["items"]
        }
        webhooks = shop.get(f"{shop.base}/webhooks").json()["items"]
        owner_id = str(
            shop.client.get("/v1/me", headers=shop.headers).json()["user"]["id"]
        )
        deletions = key_deletions(shop)

    assert hooked.status_code == 201, hooked.text
    assert before.status_code == 200, before.text
    assert removed.status_code == 204, removed.text
    assert their_key.status_code == 401
    assert our_key.status_code == 200, our_key.text
    # The removed person's own token: the business is gone for them.
    assert their_session.status_code == 404
    assert their_bookings.status_code == 404
    assert keys["Their Zapier"]["status"] == "revoked"
    assert keys["Our CRM"]["status"] == "active"
    assert webhooks == []
    assert deletions == [(owner_id, keys["Their Zapier"]["id"])]


def test_removing_a_member_without_keys_revokes_nothing() -> None:
    with open_integration_shop() as shop:
        _, member_id = co_owner_token(shop)
        ours = shop.add_api_key()

        removed = shop.delete(f"{shop.base}/members/{member_id}")
        our_key = shop.api("GET", "/me", ours)
        deletions = key_deletions(shop)

    assert removed.status_code == 204, removed.text
    assert our_key.status_code == 200
    assert deletions == []
