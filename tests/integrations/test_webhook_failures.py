"""
A receiver that fails: retries with backoff until it answers, an endpoint
turned off after WEBHOOK_DISABLE_AFTER_FAILURES failures in a row (or at
once on 410 Gone), deliveries given up after a day and retried by hand.
"""

from tests.integrations.fake_webhook_poster import answer
from tests.integrations.integration_shop import open_integration_shop

HOUR: int = 60 * 60


def test_a_failed_delivery_is_retried_until_the_receiver_answers() -> None:
    with open_integration_shop() as shop:
        webhook = shop.add_webhook()["endpoint"]
        shop.receivers.answer_next(answer(500))
        shop.book()
        shop.run_jobs()
        first = shop.deliveries(webhook["id"])[0]
        failing = shop.get(f"{shop.base}/webhooks").json()["items"][0]
        shop.run_jobs()
        too_early = len(shop.receivers.posted)
        shop.workshop.clock.advance(60)
        shop.run_jobs()
        second = shop.deliveries(webhook["id"])[0]
        healthy = shop.get(f"{shop.base}/webhooks").json()["items"][0]

    assert first["status"] == "pending"
    assert first["attempts"] == 1
    assert first["last_status_code"] == 500
    assert first["last_problem"] == "http_status"
    assert 24 * 1_000_000 <= first["next_attempt_at"] - first["last_attempt_at"]
    assert first["next_attempt_at"] - first["last_attempt_at"] <= 36 * 1_000_000
    assert failing["consecutive_failures"] == 1
    assert too_early == 1
    assert second["status"] == "delivered"
    assert second["attempts"] == 2
    assert healthy["consecutive_failures"] == 0


def test_an_endpoint_failing_again_and_again_is_disabled() -> None:
    with open_integration_shop({"WEBHOOK_DISABLE_AFTER_FAILURES": "2"}) as shop:
        webhook = shop.add_webhook()["endpoint"]
        shop.receivers.answer_next(answer(503), answer(503))
        shop.book("13:00")
        shop.run_jobs()
        shop.book("14:00", name="Giorgi")
        shop.run_jobs()
        disabled = shop.get(f"{shop.base}/webhooks").json()["items"][0]
        shop.book("15:00", name="Mariam")
        shop.run_jobs()
        logged = shop.deliveries(webhook["id"])
        enabled = shop.patch(
            f"{shop.base}/webhooks/{webhook['id']}", {"status": "active"}
        ).json()

    assert disabled["status"] == "disabled"
    assert disabled["consecutive_failures"] == 2
    assert disabled["disabled_at"] is not None
    assert len(shop.receivers.posted) == 2
    assert len(logged) == 2
    assert enabled["status"] == "active"
    assert enabled["consecutive_failures"] == 0
    assert enabled["disabled_at"] is None


def test_410_gone_disables_the_endpoint_at_once() -> None:
    with open_integration_shop() as shop:
        webhook = shop.add_webhook()["endpoint"]
        shop.receivers.answer_next(answer(410))
        shop.book()
        shop.run_jobs()
        delivery = shop.deliveries(webhook["id"])[0]
        endpoint = shop.get(f"{shop.base}/webhooks").json()["items"][0]

    assert delivery["status"] == "failed"
    assert delivery["last_problem"] == "gone"
    assert delivery["next_attempt_at"] is None
    assert endpoint["status"] == "disabled"


def test_a_delivery_is_given_up_after_a_day_and_can_be_retried() -> None:
    with open_integration_shop() as shop:
        webhook = shop.add_webhook()["endpoint"]
        shop.receivers.answer_next(*[answer(500)] * 20)
        shop.book()
        for _ in range(8):
            shop.run_jobs()
            shop.workshop.clock.advance(10 * HOUR)
        given_up = shop.deliveries(webhook["id"])[0]
        tries = len(shop.receivers.posted)
        shop.receivers.answers.clear()
        retried = shop.post(f"{shop.base}/webhook-deliveries/{given_up['id']}/retry")
        shop.run_jobs()
        delivered = shop.deliveries(webhook["id"])[0]

    assert given_up["status"] == "failed"
    assert given_up["next_attempt_at"] is None
    assert 4 <= tries <= 8
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "pending"
    assert delivered["status"] == "delivered"
    assert delivered["attempts"] == tries + 1


def test_a_paused_endpoint_gets_nothing_new() -> None:
    with open_integration_shop() as shop:
        webhook = shop.add_webhook()["endpoint"]
        paused = shop.patch(
            f"{shop.base}/webhooks/{webhook['id']}", {"status": "paused"}
        )
        shop.book()
        shop.run_jobs()
        logged = shop.deliveries(webhook["id"])

    assert paused.json()["status"] == "paused"
    assert logged == []
    assert shop.receivers.posted == []
