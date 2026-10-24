"""
The webhooks' delivery log and the customers' privacy: erasing a customer
deletes the deliveries about them, and the log forgets everything after 30
days (the daily purge).
"""

from app.schemas.domain.webhooks import WebhookDeliveryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.integrations.prefixed_id import WebhookDeliveryId
from tests.integrations.integration_shop import IntegrationShop, open_integration_shop

DAY: int = 24 * 60 * 60


def test_erasing_a_customer_deletes_the_deliveries_about_them() -> None:
    with open_integration_shop() as shop:
        webhook = shop.add_webhook()["endpoint"]
        booking = shop.book()
        shop.run_jobs()
        before = shop.deliveries(webhook["id"])
        erased = shop.delete(f"{shop.base}/contacts/{booking['contact_id']}")
        after = shop.deliveries(webhook["id"])

    assert len(before) == 1
    assert erased.status_code == 204, erased.text
    assert after == []


def stored(shop: IntegrationShop, delivery_id: str) -> WebhookDeliveryDocument | None:
    container = shop.workshop.container
    business_id = BusinessId(shop.business_id)
    with container.utilities.storage_scope().scoped_to_business(business_id):
        return container.repositories.webhook_delivery_repo().get(
            business_id, WebhookDeliveryId(delivery_id)
        )


def test_the_daily_purge_forgets_deliveries_after_thirty_days() -> None:
    with open_integration_shop() as shop:
        webhook = shop.add_webhook()["endpoint"]
        shop.book()
        shop.run_jobs()
        delivery_id = str(shop.deliveries(webhook["id"])[0]["id"])
        worker = shop.workshop.container.gateways.background_worker()
        shop.workshop.clock.advance(29 * DAY)
        worker.run_once()
        kept = stored(shop, delivery_id)
        shop.workshop.clock.advance(2 * DAY)
        worker.run_once()
        purged = stored(shop, delivery_id)

    assert kept is not None
    assert purged is None
