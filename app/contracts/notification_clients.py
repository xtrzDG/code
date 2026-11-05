"""The provider of device notifications (Web Push)."""

from typing import Protocol

from app.contracts.client_contract import ClientContract
from app.schemas.dto.notifications.web_push import WebPushMessage
from app.schemas.typings.notifications.constrained_strings import VapidPublicKey


class WebPushClientContract(ClientContract, Protocol):
    @property
    def public_key(self) -> VapidPublicKey:
        """The platform key browsers subscribe with."""
        raise NotImplementedError

    def send(self, message: WebPushMessage) -> None:
        """
        Encrypt the payload for the subscription and post it to its push
        service. Raises PushSubscriptionGoneError (the subscription is no
        more), ProviderRateLimitedError, ProviderRejectedMessageError or
        ExternalServiceError (network, 5xx: worth another try).
        """
        raise NotImplementedError
