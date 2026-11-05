"""A fake Web Push client and in-memory notification repositories."""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.notification_clients import WebPushClientContract
from app.repositories.notification_repositories import StaffDeliveryStateRepository
from app.schemas.domain.staff_deliveries import StaffDeliveryStateDocument
from app.schemas.dto.notifications.web_push import WebPushMessage
from app.schemas.typings.notifications.constrained_strings import VapidPublicKey

FAKE_VAPID_PUBLIC_KEY: VapidPublicKey = VapidPublicKey(
    "BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8"
)


class FakeWebPushClient(WebPushClientContract):
    """Records what would be pushed; raises `error` when one is set."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error: Exception | None = error
        self.sent: list[WebPushMessage] = []

    @property
    def public_key(self) -> VapidPublicKey:
        return FAKE_VAPID_PUBLIC_KEY

    def send(self, message: WebPushMessage) -> None:
        if self.error is not None:
            raise self.error

        self.sent.append(message)


def staff_delivery_state_repo() -> StaffDeliveryStateRepository:
    return StaffDeliveryStateRepository(
        InMemoryDocumentCollectionAdapter[StaffDeliveryStateDocument](
            StaffDeliveryStateDocument
        )
    )
