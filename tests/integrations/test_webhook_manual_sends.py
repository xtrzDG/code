"""
Webhook requests sent by hand (test events and retries from the log) are
limited per business, so a script repeating them cannot use the platform
to flood an outside server.
"""

from app.use_cases.integrations.manual_webhook_sends import MANUAL_SENDS_PER_MINUTE
from tests.integrations.integration_shop import open_integration_shop


def test_test_events_and_retries_share_a_limit_per_minute() -> None:
    with open_integration_shop() as shop:
        webhook = shop.add_webhook()["endpoint"]
        shop.book()
        shop.run_jobs()
        delivery = shop.deliveries(webhook["id"])[0]
        test_path = f"{shop.base}/webhooks/{webhook['id']}/test"
        retry_path = f"{shop.base}/webhook-deliveries/{delivery['id']}/retry"
        sent = [
            shop.post(test_path).status_code
            for _ in range(int(MANUAL_SENDS_PER_MINUTE) - 1)
        ]
        retried = shop.post(retry_path)
        refused_test = shop.post(test_path)
        refused_retry = shop.post(retry_path)
        posted = len(shop.receivers.posted)
        shop.workshop.clock.advance(121)
        later = shop.post(test_path)

    assert set(sent) == {200}
    assert retried.status_code == 200, retried.text
    assert refused_test.status_code == 429
    assert refused_test.json()["error"] == "rate_limited"
    assert int(refused_test.headers["Retry-After"]) >= 1
    assert refused_retry.status_code == 429
    # The booking's delivery and nine test events (the retry waits for its
    # job); the refused ones sent nothing.
    assert posted == 1 + int(MANUAL_SENDS_PER_MINUTE) - 1
    assert later.status_code == 200, later.text
