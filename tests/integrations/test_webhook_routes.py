"""Settings → Integrations → Webhooks through the cabinet's API."""

from tests.integrations.fake_webhook_poster import answer
from tests.integrations.integration_shop import RECEIVER_URL, open_integration_shop


def test_the_owner_lists_changes_and_deletes_a_webhook() -> None:
    with open_integration_shop() as shop:
        empty = shop.get(f"{shop.base}/webhooks").json()
        webhook = shop.add_webhook(["booking.created"])["endpoint"]
        path = f"{shop.base}/webhooks/{webhook['id']}"
        changed = shop.patch(
            path,
            {"label": "Sheets", "event_types": ["lead.created", "booking.created"]},
        )
        refused = shop.patch(path, {"status": "disabled"})
        deleted = shop.delete(path)
        gone = shop.patch(path, {"label": "Again"})
        after = shop.get(f"{shop.base}/webhooks").json()

    assert empty["items"] == []
    assert "webhook.test" not in empty["event_types"]
    assert "booking.created" in empty["event_types"]
    assert empty["max_endpoints"] == 10
    assert empty["failures_before_disable"] == 15
    assert webhook["status"] == "active"
    assert webhook["origin"] == "cabinet"
    assert changed.status_code == 200, changed.text
    assert changed.json()["label"] == "Sheets"
    assert changed.json()["event_types"] == ["booking.created", "lead.created"]
    assert refused.status_code == 422
    assert deleted.status_code == 204
    assert gone.status_code == 404
    assert after["items"] == []


def test_a_private_or_plain_http_address_is_refused() -> None:
    with open_integration_shop() as shop:
        private = shop.post(
            f"{shop.base}/webhooks",
            {"url": "https://localhost/hook", "event_types": ["booking.created"]},
        )
        plain = shop.post(
            f"{shop.base}/webhooks",
            {"url": "http://hooks.example.com/x", "event_types": ["booking.created"]},
        )
        test_event = shop.post(
            f"{shop.base}/webhooks",
            {"url": RECEIVER_URL, "event_types": ["webhook.test"]},
        )

    assert private.status_code == 422
    assert private.json()["reasons"][0]["code"] == "not_public"
    assert plain.status_code == 422
    assert test_event.status_code == 422


def test_a_business_has_at_most_ten_webhooks() -> None:
    with open_integration_shop() as shop:
        for number in range(10):
            shop.add_webhook(url=f"{RECEIVER_URL}/{number}")
        eleventh = shop.post(
            f"{shop.base}/webhooks",
            {"url": RECEIVER_URL, "event_types": ["booking.created"]},
        )

    assert eleventh.status_code == 409
    assert eleventh.json()["reasons"][0]["code"] == "webhook_limit_reached"


def test_a_rotated_secret_is_shown_once_and_signs_from_then_on() -> None:
    with open_integration_shop() as shop:
        created = shop.add_webhook()
        rotated = shop.post(
            f"{shop.base}/webhooks/{created['endpoint']['id']}/rotate-secret"
        ).json()

    assert rotated["signing_secret"] != created["signing_secret"]
    assert rotated["endpoint"]["secret_hint"] == rotated["signing_secret"][-4:]


def test_send_test_event_posts_now_and_does_not_count_as_a_failure() -> None:
    with open_integration_shop() as shop:
        webhook = shop.add_webhook()["endpoint"]
        sent = shop.post(f"{shop.base}/webhooks/{webhook['id']}/test")
        shop.receivers.answer_next(answer(500))
        failed = shop.post(f"{shop.base}/webhooks/{webhook['id']}/test")
        endpoint = shop.get(f"{shop.base}/webhooks").json()["items"][0]
        detail = shop.get(f"{shop.base}/webhook-deliveries/{sent.json()['id']}")

    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "delivered"
    assert sent.json()["is_test"] is True
    assert sent.json()["event_type"] == "webhook.test"
    assert failed.json()["status"] == "failed"
    assert endpoint["consecutive_failures"] == 0
    assert [str(request.event_type) for request in shop.receivers.posted] == [
        "webhook.test",
        "webhook.test",
    ]
    assert detail.status_code == 200, detail.text
    assert webhook["id"] in detail.json()["payload"]
