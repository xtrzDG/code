"""Failures of staff notifications that their senders act on."""

from app.schemas.exceptions.application_errors import ProviderRejectedMessageError


class PushSubscriptionGoneError(ProviderRejectedMessageError):
    """
    The push service no longer knows a device subscription (HTTP 404 or
    410: the user blocked notifications or removed the app; 403: it was
    made with another platform key). It can never work again, so it is
    deleted.
    """
