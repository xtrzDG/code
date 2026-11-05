"""
The whole application: a webhook switched off after failures in a row
reaches the owner's Telegram once (through the outbox), with a link to
Settings → Integrations and an entry in the audit log; switched on and
failing again, it reaches them again.
"""

from typing import Any

from tests.integrations.fake_webhook_poster import answer
from tests.integrations.integration_shop import IntegrationShop, open_integration_shop

OWNER_CHAT: str = "70001"


def follow_by_telegram(shop: IntegrationShop) -> None:
    saved = shop.patch(
        shop.base,
        {
            "manager_contacts": [
                {
                    "name": "Nino",
                    "channel": "telegram",
                    "address": OWNER_CHAT,
                    "language": "en",
                }
            ]
        },
    )
    assert saved.status_code == 200, saved.text


def alerts(shop: IntegrationShop) -> list[str]:
    return [
        str(body["text"])
        for body in shop.workshop.telegram.bodies("sendMessage")
        if body.get("chat_id") == OWNER_CHAT
        and "webhook was switched off" in str(body["text"])
    ]


def fail_twice(shop: IntegrationShop, first: str, second: str) -> None:
    shop.receivers.answer_next(answer(503), answer(503))
    for time, name in ((first, "Nino"), (second, "Giorgi")):
        shop.book(time, name=name)
        # Delivers the webhook, then the outbox (the alert).
        shop.run_jobs()
        shop.run_jobs()


def test_a_switched_off_webhook_reaches_the_owner_once_per_switch_off() -> None:
    with open_integration_shop({"WEBHOOK_DISABLE_AFTER_FAILURES": "2"}) as shop:
        follow_by_telegram(shop)
        webhook = shop.add_webhook()["endpoint"]

        fail_twice(shop, "12:00", "13:00")
        once = alerts(shop)
        shop.book("14:00", name="Mariam")
        shop.run_jobs()
        shop.run_jobs()
        still_once = alerts(shop)
        switched_on = shop.patch(
            f"{shop.base}/webhooks/{webhook['id']}", {"status": "active"}
        )
        fail_twice(shop, "15:00", "16:00")
        twice = alerts(shop)
        token = once[0].rsplit("/", 1)[-1]
        link = shop.get(f"{shop.base}/notification-links/{token}")
        log: list[dict[str, Any]] = shop.get(f"{shop.base}/audit-log").json()["items"]

    assert len(once) == 1
    assert "The address CRM gets no more events after 2 failed attempts" in once[0]
    assert link.status_code == 200, link.text
    assert link.json()["target"] == "integrations"
    assert still_once == once
    assert switched_on.status_code == 200
    assert len(twice) == 2
    automatic = [
        entry
        for entry in log
        if entry["entity"] == "webhook_endpoint" and entry["actor_id"] is None
    ]
    assert len(automatic) == 2
