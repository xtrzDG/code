"""Settings → Integrations → API keys, and what a key can then do."""

from tests.integrations.integration_shop import open_integration_shop


def test_a_new_key_is_shown_once_and_opens_the_public_api() -> None:
    with open_integration_shop() as shop:
        created = shop.post(
            f"{shop.base}/api-keys", {"name": "Zapier", "scopes": ["leads:read"]}
        ).json()
        listed = shop.get(f"{shop.base}/api-keys").json()
        me = shop.api("GET", "/me", created["token"])
        after_use = shop.get(f"{shop.base}/api-keys").json()["items"][0]

    token = str(created["token"])
    assert token.startswith(created["api_key"]["prefix"] + "_")
    assert token not in str(listed)
    assert listed["items"][0]["name"] == "Zapier"
    assert listed["items"][0]["scopes"] == ["leads:read"]
    assert listed["items"][0]["last_used_at"] is None
    assert listed["max_keys"] == 10
    assert listed["requests_per_minute"] == 120
    assert "webhooks:manage" in listed["scopes"]
    assert me.status_code == 200, me.text
    assert me.json()["business_id"] == shop.business_id
    assert me.json()["business_name"] == "Salobie Bia"
    assert me.json()["scopes"] == ["leads:read"]
    assert after_use["last_used_at"] is not None


def test_a_revoked_key_stops_at_once_and_takes_its_webhooks() -> None:
    with open_integration_shop() as shop:
        token = shop.add_api_key()
        key_id = shop.get(f"{shop.base}/api-keys").json()["items"][0]["id"]
        subscribed = shop.api(
            "POST",
            "/webhooks",
            token,
            {"url": "https://hooks.zapier.com/1", "event_types": ["lead.created"]},
        )
        revoked = shop.delete(f"{shop.base}/api-keys/{key_id}")
        again = shop.delete(f"{shop.base}/api-keys/{key_id}")
        refused = shop.api("GET", "/me", token)
        listed = shop.get(f"{shop.base}/api-keys").json()["items"][0]
        webhooks = shop.get(f"{shop.base}/webhooks").json()["items"]

    assert subscribed.status_code == 201, subscribed.text
    assert revoked.status_code == 204
    assert again.status_code == 204
    assert refused.status_code == 401
    assert listed["status"] == "revoked"
    assert listed["revoked_at"] is not None
    assert webhooks == []


def test_unknown_or_malformed_keys_are_refused() -> None:
    with open_integration_shop() as shop:
        shop.add_api_key()
        missing = shop.client.get("/v1/public-api/me")
        malformed = shop.api("GET", "/me", "not-a-key")
        unknown = shop.api("GET", "/me", "awk_abcd2345_" + "A" * 40)
        cabinet_token = shop.client.get("/v1/public-api/me", headers=shop.headers)

    assert [missing.status_code, malformed.status_code, unknown.status_code] == [
        401,
        401,
        401,
    ]
    assert cabinet_token.status_code == 401


def test_a_business_has_at_most_ten_active_keys() -> None:
    with open_integration_shop() as shop:
        for number in range(10):
            shop.add_api_key(name=f"Key {number}")
        eleventh = shop.post(
            f"{shop.base}/api-keys", {"name": "One more", "scopes": ["leads:read"]}
        )
        no_scope = shop.post(f"{shop.base}/api-keys", {"name": "Empty", "scopes": []})

    assert eleventh.status_code == 409
    assert eleventh.json()["reasons"][0]["code"] == "api_key_limit_reached"
    assert no_scope.status_code == 422
