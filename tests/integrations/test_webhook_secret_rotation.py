"""
A key rotation seals the webhooks' signing secrets again: each with the
current key, a secret rotated meanwhile kept as it is, an unreadable one
left for the run's count; deliveries keep their valid signatures after.
"""

import json

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.use_cases.admin.security.webhook_secret_resealer import (
    reseal_webhook_endpoints,
)
from tests.integrations.integration_shop import (
    RECEIVER_URL,
    IntegrationShop,
    open_integration_shop,
)
from tests.integrations.webhook_receivers import is_valid_signature


def sealed_secrets(shop: IntegrationShop) -> list[str]:
    container = shop.workshop.container
    business_id = BusinessId(shop.business_id)
    with container.utilities.storage_scope().scoped_to_business(business_id):
        endpoints = container.repositories.webhook_endpoint_repo().list_by_business(
            business_id
        )
    return [str(endpoint.encrypted_secret) for endpoint in endpoints]


def test_webhook_secrets_are_sealed_again_with_the_current_key() -> None:
    with open_integration_shop() as shop:
        created = shop.add_webhook()
        shop.add_webhook(url="https://hooks.example.com/second")
        before = sealed_secrets(shop)
        container = shop.workshop.container
        cipher = container.adapters.secret_cipher()
        business_id = BusinessId(shop.business_id)

        def reseal(encrypted: EncryptedChannelSecret) -> EncryptedChannelSecret | None:
            if str(encrypted) == before[1]:
                return None  # unreadable: left for the run's count
            return cipher.encrypt(cipher.decrypt(encrypted))

        with container.utilities.storage_scope().scoped_to_business(business_id):
            reseal_webhook_endpoints(
                container.repositories.webhook_endpoint_repo(), business_id, reseal
            )
        after = sealed_secrets(shop)
        shop.book()
        shop.run_jobs()
        request = next(
            item for item in shop.receivers.posted if str(item.url) == RECEIVER_URL
        )
        now_seconds = int(shop.workshop.clock.wall_clock.now_unix()) // 1_000_000

    assert after[0] != before[0]
    assert after[1] == before[1]
    assert json.loads(str(request.body))["type"] == "booking.created"
    assert is_valid_signature(
        str(created["signing_secret"]),
        str(request.signature),
        str(request.body),
        now_seconds,
    )
