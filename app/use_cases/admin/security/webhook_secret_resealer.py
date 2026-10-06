"""
Seal the signing secrets of a business's outbound webhooks again with the
current key, each written back only if it did not change meanwhile (a
secret rotated by its owner is sealed with the current key already).
"""

from collections.abc import Callable

from app.contracts.repositories.integration_repositories import (
    WebhookEndpointRepoContract,
)
from app.schemas.domain.webhooks import WebhookEndpointDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret

type Reseal = Callable[[EncryptedChannelSecret], EncryptedChannelSecret | None]


def reseal_webhook_endpoints(
    endpoint_repo: WebhookEndpointRepoContract,
    business_id: BusinessId,
    reseal: Reseal,
) -> None:
    """Every webhook signing secret of the business under the current key."""

    for endpoint in endpoint_repo.list_by_business(business_id):
        sealed = reseal(endpoint.encrypted_secret)
        if sealed is None or sealed == endpoint.encrypted_secret:
            continue

        endpoint_repo.update(
            business_id, endpoint.id, replacing(endpoint.encrypted_secret, sealed)
        )


def replacing(
    previous: EncryptedChannelSecret, sealed: EncryptedChannelSecret
) -> Callable[[WebhookEndpointDocument], WebhookEndpointDocument | None]:
    def replace(stored: WebhookEndpointDocument) -> WebhookEndpointDocument | None:
        if stored.encrypted_secret != previous:
            return None  # Rotated meanwhile: sealed with the current key.

        return stored.model_copy(update={"encrypted_secret": sealed})

    return replace
